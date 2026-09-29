"""Ferramentas — análise avulsa (Qwen local), mídia (LLaVA), conversor PDF, intimações."""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Job
from app.services import get_db
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/ferramentas", tags=["ferramentas"])

# Auto-Laudo Pro: modularized laudo auto-generation (Wave 1)
# Note: auto_laudo_pro is now loaded via ferramentas module auto-discovery
# This legacy import kept for backward compatibility
try:
    from app.modules.ferramentas.auto_laudo_pro import auto_laudo_pro_router
    router.include_router(auto_laudo_pro_router)
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"⚠️ Falha ao carregar auto_laudo_pro: {e}")

UPLOAD_DIR = "/app/uploads"
MAX_UPLOAD_MB = 80

@router.get("")
async def listar_ferramentas():
    """Lista todas as ferramentas disponíveis"""
    return {
        "ferramentas": [
            {"id": "analisar", "titulo": "Análise IA", "desc": "Qwen 3.6 local", "icon": "🧠"},
            {"id": "midia", "titulo": "Fake Media Detector", "desc": "Análise de deepfake", "icon": "🔍"},
            {"id": "pdf", "titulo": "Conversor PDF", "desc": "Extração de texto", "icon": "📄"},
            {"id": "esaj", "titulo": "Busca ESAJ", "desc": "Intimações e autos", "icon": "🔎"},
        ]
    }


async def _salvar_upload(arquivo: UploadFile) -> str:
    dados = await arquivo.read()
    if len(dados) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Arquivo acima de {MAX_UPLOAD_MB}MB")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(arquivo.filename or "")[1][:8]
    destino = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(destino, "wb") as f:
        f.write(dados)
    return destino


class AnaliseTexto(BaseModel):
    texto: str


@router.post("/analisar")
async def analisar_texto(
    payload: AnaliseTexto,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enfileira a análise do texto colado para o Qwen local do Mac.
    Retorna job_id; o front consulta GET /api/v1/jobs/{id} até concluir."""
    if not payload.texto.strip():
        raise HTTPException(status_code=400, detail="Cole o texto do processo/intimação")
    job = Job(tipo="analise_ia", payload={"conteudo": payload.texto[:15000]}, status="na_fila")
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "status": "na_fila",
            "mensagem": "Análise enviada ao Qwen local. Acompanhe o resultado."}


@router.post("/analisar-midia")
async def analisar_midia(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Análise forense de mídia (imagem/vídeo): EXIF/hash/risco + descrição LLaVA.
    Roda no agente Mac. Retorna job_id."""
    caminho = await _salvar_upload(arquivo)
    job = Job(tipo="analise_midia", status="na_fila",
              payload={"arquivo_path": caminho, "nome": arquivo.filename})
    db.add(job); db.commit(); db.refresh(job)
    return {"job_id": job.id, "mensagem": "Analisando a mídia no Mac (LLaVA + detector)."}


@router.post("/converter-pdf")
async def converter_pdf(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Extrai o texto de um PDF (por página), no agente Mac. Retorna job_id."""
    caminho = await _salvar_upload(arquivo)
    job = Job(tipo="converter_pdf", status="na_fila",
              payload={"arquivo_path": caminho, "nome": arquivo.filename})
    db.add(job); db.commit(); db.refresh(job)
    return {"job_id": job.id, "mensagem": "Convertendo o PDF no Mac."}


@router.post("/projuris/sincronizar-agora")
async def sincronizar_projuris_agora(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sincroniza todos os processos do Projuris AGORA (síncrono)."""
    import httpx
    from app.services.importer import upsert_processo

    base_url = os.environ.get("PROJURIS_BASE_URL", "").rstrip("/")
    token = os.environ.get("PROJURIS_TOKEN", "")

    if not base_url or not token:
        return {
            "status": "erro",
            "mensagem": "Projuris não configurado. Defina PROJURIS_BASE_URL e PROJURIS_TOKEN no .env",
        }

    criados, atualizados = 0
    erros = []

    try:
        with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as client:
            for pagina in range(1, 100):  # Max 100 páginas
                resp = client.get(f"{base_url}/processos", params={"pagina": pagina, "limit": 50})

                if resp.status_code == 401:
                    return {"status": "erro", "mensagem": "Token Projuris inválido (401)"}

                if resp.status_code != 200:
                    break

                corpo = resp.json()
                itens = corpo if isinstance(corpo, list) else corpo.get("itens") or corpo.get("content") or []

                if not itens:
                    break

                for item in itens:
                    try:
                        def mapear_projuris(i):
                            return {
                                "external_id": str(i.get("id") or i.get("processoId") or ""),
                                "numero_cnj": i.get("numeroCnj") or i.get("numero") or "",
                                "titulo": i.get("titulo") or i.get("pasta"),
                                "autor": i.get("autor") or (i.get("parteAtiva", {}).get("nome") if isinstance(i.get("parteAtiva"), dict) else i.get("parteAtiva")),
                                "reu": i.get("reu") or (i.get("partePassiva", {}).get("nome") if isinstance(i.get("partePassiva"), dict) else i.get("partePassiva")),
                                "vara": i.get("vara"),
                                "tribunal": i.get("tribunal") or i.get("orgao"),
                                "juiz": i.get("juiz"),
                                "especialidade": i.get("area") or i.get("especialidade"),
                                "status": i.get("status") or "ativo",
                            }

                        _, criado = upsert_processo(db, mapear_projuris(item), source_system="projuris")
                        criados += criado
                        atualizados += not criado
                    except ValueError as e:
                        erros.append(str(e))

        db.commit()

    except Exception as e:
        db.rollback()
        return {
            "status": "erro",
            "mensagem": str(e),
        }

    return {
        "status": "sucesso",
        "criados": criados,
        "atualizados": atualizados,
        "erros": len(erros),
        "mensagem": f"✅ {criados} novos processos importados, {atualizados} atualizados",
    }


@router.post("/buscar-intimacoes")
async def buscar_intimacoes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """FERRAMENTA COMPLETA: busca intimações (email + ESAJ + Projuris) + baixa autos + extrai ofícios."""
    from app.workers import monitor_emails

    # 1) Email
    emails = 0
    try:
        emails = monitor_emails.processar_caixa_entrada()
    except Exception:
        pass

    # 2) ESAJ (se Windows com A3, roda lá; se Mac, roda aqui)
    ja = db.query(Job).filter(Job.tipo == "esaj_intimacoes",
                              Job.status.in_(["na_fila", "processando"])).first()
    if not ja:
        db.add(Job(tipo="esaj_intimacoes", status="na_fila",
                   payload={"origem": "manual", "include_projuris": True}))
        db.commit()

    # 3) Projuris (buscar dados de processo não-intimação)
    db.add(Job(tipo="projuris_sync", status="na_fila", payload={"origem": "manual"}))
    db.commit()

    return {
        "emails_processados": emails,
        "esaj": "na fila" if not ja else "já em andamento",
        "projuris": "sincronizando",
        "status": "busca completa iniciada"
    }


@router.get("/status-automacao")
async def status_automacao(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Estado das automações para a página de ferramentas."""
    import os
    from app.workers import monitor_emails
    return {
        "monitor_email": monitor_emails.configurado(),
        "busca_esaj": os.environ.get("ESAJ_BUSCA_AUTOMATICA", "1") == "1",
        "analise_ia": "Qwen local (agente Mac)",
    }


@router.post("/buscar-intimacoes-esaj")
async def buscar_intimacoes_esaj_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Busca intimações ESAJ com automação de browser (browser-use + LLM)."""
    try:
        from app.services.esaj_browser_automation import buscar_intimacoes_esaj
        resultado = buscar_intimacoes_esaj(
            os.environ.get("CPF_ESAJ", ""),
            os.environ.get("SENHA_ESAJ", "")
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro busca ESAJ: {str(e)}")
