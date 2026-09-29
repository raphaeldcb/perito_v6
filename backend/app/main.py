import sys
import os
import signal
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.services import init_db
from app.services.health_check import get_health_status
from app.middleware.audit_log import AuditLogMiddleware
from app.middleware.rate_limiting import limiter
from app.routes import router as api_router

logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Perito System v6.0 - Professional API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Attach rate limiter to app (for slowapi integration)
app.state.limiter = limiter

# Audit Log Middleware (deve estar antes de CORS para capturar tudo)
app.add_middleware(AuditLogMiddleware)

# CORS Middleware — Explicit, no wildcards (Security P1)
# Allow specific origins, methods, and headers only
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,  # Only: GET, POST, PATCH, DELETE (not *)
    allow_headers=settings.cors_headers,  # Only: Content-Type, Authorization (not *)
)

# Include API routers
app.include_router(api_router)

# Distribuição estática do AssistProduction Windows Agent (.exe + manifesto
# de auto-update). Sem autenticação de propósito — é só um binário público
# igual qualquer instalador de app desktop; o valor sensível é a
# AGENT_API_KEY, que nunca fica aqui, só no config.json gravado pelo
# instalador na máquina do colaborador. Gerado por tools/build_assistproduction_exe.py.
_assistprod_static_dir = os.path.join(os.path.dirname(__file__), "static", "assistproduction")
os.makedirs(_assistprod_static_dir, exist_ok=True)
app.mount("/static/assistproduction", StaticFiles(directory=_assistprod_static_dir), name="assistproduction-static")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ Database initialized")

    # P0 Security: File cleanup scheduler (SECURITY_FIXES_PHASE1)
    try:
        from app.services.oficio_campo_mapeador import start_cleanup_scheduler
        start_cleanup_scheduler()
        print("✅ File cleanup scheduler iniciado (limpeza a cada 30 min)")
    except Exception as e:
        print(f"⚠️ Falha ao iniciar cleanup scheduler: {e}")

    # Templates de ofício vivem no layer efêmero do container — recria se faltar
    try:
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        if not os.path.exists(os.path.join(templates_dir, "oficio_requerimento.docx")):
            from app.services.create_oficio_templates import criar_templates
            criar_templates()
            print("✅ Templates de ofício criados")
    except Exception as e:
        print(f"⚠️ Falha ao criar templates de ofício: {e}")

    # OneDrive Sync Scheduler (FASE 3)
    if os.getenv("ONEDRIVE_SYNC_ENABLED", "false").lower() == "true":
        try:
            from app.workers.onedrive_sync_worker import iniciar_scheduler_onedrive
            iniciar_scheduler_onedrive()
            print("✅ OneDrive sync scheduler iniciado")
        except Exception as e:
            print(f"⚠️ Falha ao iniciar OneDrive sync scheduler: {e}")

    # Cleanup de audit logs antigos (retention 30 dias)
    try:
        from app.middleware.audit_log import cleanup_old_audit_logs
        cleanup_old_audit_logs()
        print("✅ Audit logs cleanup feito (retention 30 dias)")
    except Exception as e:
        print(f"⚠️ Falha ao limpar audit logs: {e}")

    # Microsoft Graph API Monitoring — Comunicações Judiciais (5 min interval)
    try:
        from app.workers.scheduler_comunicacoes import inicializar_scheduler
        inicializar_scheduler()
        print("✅ Scheduler de comunicações via Graph API iniciado")
    except Exception as e:
        print(f"⚠️ Falha ao iniciar scheduler de comunicações: {e}")

    # AssistProduction ↔ Financeiro: agregação noturna de custo do tempo ocioso
    if os.getenv("PRODUTIVIDADE_SYNC_ENABLED", "true").lower() == "true":
        try:
            from app.workers.produtividade_scheduler import iniciar_scheduler_produtividade
            iniciar_scheduler_produtividade()
            print("✅ Scheduler de produtividade financeira (AssistProduction) iniciado")
        except Exception as e:
            print(f"⚠️ Falha ao iniciar scheduler de produtividade: {e}")

    # Busca Automática ESAJ (DESABILITADO — use endpoints manuais)
    # try:
    #     from app.workers.esaj_intimacoes_scheduler import iniciar_scheduler_esaj
    #     iniciar_scheduler_esaj()
    #     print("✅ Scheduler ESAJ iniciado (06:00 e 20:00 UTC)")
    # except Exception as e:
    #     print(f"⚠️ Falha ao iniciar scheduler ESAJ: {e}")

    # P1: Dashboard Alertas (DESABILITADO — use endpoints manuais)
    # try:
    #     from app.workers.alerta_scheduler import iniciar_scheduler_alertas
    #     iniciar_scheduler_alertas()
    #     print("✅ Scheduler de alertas iniciado (verificação 06:00 UTC)")
    # except Exception as e:
    #     print(f"⚠️ Falha ao iniciar scheduler de alertas: {e}")

    print("ℹ️ Schedulers automáticos DESABILITADOS — use endpoints manuais conforme necessário")

    # P2: Expiração Senha + Inativação (02:00 UTC diário) — DESABILITADO até migração VPS
    # try:
    #     from app.workers.usuario_expiracao_scheduler import iniciar_scheduler_expiracao
    #     iniciar_scheduler_expiracao()
    #     print("✅ Scheduler de expiração de senha/inativação iniciado (02:00 UTC)")
    # except Exception as e:
    #     print(f"⚠️ Falha ao iniciar scheduler de expiração: {e}")

    # P2: Retenção 5 Anos (1º dia do mês, 02:00 UTC) — DESABILITADO até migração VPS
    # try:
    #     from app.workers.retencao_scheduler import iniciar_scheduler_retencao
    #     iniciar_scheduler_retencao()
    #     print("✅ Scheduler de retenção de arquivos iniciado (1º dia, 02:00 UTC)")
    # except Exception as e:
    #     print(f"⚠️ Falha ao iniciar scheduler de retenção: {e}")


# Health check - sem autenticação, com verificações profundas
@app.get("/health")
async def health_check():
    """
    Health check com verificações profundas:
    - DB conectada (test query SELECT 1)
    - Qwen respondendo (timeout 5s)
    - Fila de jobs saudável (<1000 jobs "na_fila")
    - Stale jobs check (jobs "processando" > 10min marcados como erro)

    Retorna:
    - 200 se healthy (db e qwen ok)
    - 503 se unhealthy (algum componente crítico com erro)
    """
    health_data = await get_health_status()
    http_status = health_data.pop("http_status")

    if http_status != 200:
        raise HTTPException(status_code=http_status, detail=health_data)

    return health_data


# Graceful shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🔴 Backend desligando...")
    from app.services.database import graceful_shutdown
    graceful_shutdown()
    logger.info("✅ Backend shutdown complete")


# Signal handlers for graceful shutdown (Docker SIGTERM)
def handle_shutdown_signal(signum, frame):
    logger.info(f"📴 Recebido sinal {signum} — iniciando graceful shutdown...")
    sys.exit(0)


if __name__ == "__main__":
    import uvicorn

    # Registra handlers para SIGTERM e SIGINT
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_graceful_shutdown=30,  # Timeout de 30s antes de forçar kill
    )
