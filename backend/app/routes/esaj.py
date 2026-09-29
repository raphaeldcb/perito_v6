"""Suporte ao login do ESAJ por CPF/senha + código 2FA lido do email.

O agente Mac dispara o login, o ESAJ envia o código de 6 dígitos para a caixa
ipcms@, e o agente pede esse código aqui — a VPS lê do email via Graph.
"""
import logging
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, EsajConfig, Processo, Intimacao
from app.routes.jobs import verificar_agente
from app.services import graph_mail, get_db
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/esaj", tags=["esaj"])
logger = logging.getLogger(__name__)


def _config(db: Session) -> EsajConfig:
    """FIX #3: Get-or-create padrão seguro contra race condition de múltiplas requests.

    Usa PostgreSQL UPSERT (INSERT ... ON CONFLICT) para garantir que apenas 1 config
    existe, mesmo com 2+ requests simultâneos no boot.
    """
    try:
        # Tenta encontrar
        c = db.query(EsajConfig).filter(EsajConfig.id == 1).first()
        if c:
            return c

        # Não existe: tenta criar com UPSERT
        # Se 2 requests chegam aqui ao mesmo tempo, PostgreSQL garante apenas 1 insert
        db.execute(text("""
            INSERT INTO esaj_config (id, hora, ativo, created_at, updated_at)
            VALUES (1, '03:00', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """))
        db.commit()

        # Agora busca (garantido que existe)
        c = db.query(EsajConfig).filter(EsajConfig.id == 1).first()
        if not c:
            # Último fallback (nunca deve executar)
            c = EsajConfig(id=1, hora="03:00", ativo=True)
            db.merge(c)  # Merge em vez de add (mais seguro)
            db.commit()
            db.refresh(c)
        return c
    except Exception as e:
        logger.error(f"_config falhou: {type(e).__name__}: {str(e)[:100]}")
        raise


@router.get("/agenda")
async def get_agenda(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _config(db)
    return {"hora": c.hora, "ativo": c.ativo, "ultima_execucao": c.ultima_execucao}


class AgendaInput(BaseModel):
    hora: str = "03:00"
    ativo: bool = True


@router.put("/agenda")
async def set_agenda(payload: AgendaInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _config(db)
    c.hora = payload.hora
    c.ativo = payload.ativo
    db.commit()
    return {"ok": True, "hora": c.hora, "ativo": c.ativo}


@router.get("/agenda-agente")
async def agenda_agente(db: Session = Depends(get_db), _=Depends(verificar_agente)):
    """O agente Mac lê aqui o horário da busca diária (e se já rodou hoje)."""
    c = _config(db)
    return {"hora": c.hora, "ativo": c.ativo, "ultima_execucao": c.ultima_execucao}


@router.post("/agenda-agente/executado")
async def agenda_executado(db: Session = Depends(get_db), _=Depends(verificar_agente)):
    from datetime import datetime
    c = _config(db)
    c.ultima_execucao = datetime.now().isoformat()
    db.commit()
    return {"ok": True}


class IntimacaoDia(BaseModel):
    numero: str
    classe: str | None = None
    foro: str | None = None
    vara: str | None = None
    prazo: str | None = None
    baixado: bool = False


class ListaDia(BaseModel):
    intimacoes: list[IntimacaoDia]


@router.post("/intimacoes-do-dia")
async def intimacoes_do_dia(payload: ListaDia, db: Session = Depends(get_db), _=Depends(verificar_agente)):
    """Recebe a lista de intimações do dia (do agente Mac): salva como intimação
    (dedup) e envia o resumo por e-mail ao Bruno."""
    from datetime import datetime
    novas = 0
    for it in payload.intimacoes:
        cnj = (it.numero or "").strip()
        if not cnj:
            continue
        proc = db.query(Processo).filter(Processo.numero_cnj == cnj).first()
        if not proc:
            proc = Processo(numero_cnj=cnj, titulo=f"Processo {cnj}", tribunal="TJMS",
                            vara=it.vara, status="ativo", source_system="esaj")
            db.add(proc); db.flush()
        ext = f"esaj-dia:{cnj}:{datetime.now().date().isoformat()}"
        if db.query(Intimacao).filter(Intimacao.external_id == ext).first():
            continue
        db.add(Intimacao(processo_id=proc.id, origem="esaj", tipo="intimacao",
                         assunto=(it.classe or "Intimação ESAJ"), status="pendente",
                         external_id=ext, source_system="esaj"))
        novas += 1
    db.commit()

    # e-mail resumo ao Bruno
    linhas = "".join(
        f"<tr><td>{i.numero}</td><td>{i.classe or ''}</td><td>{i.vara or i.foro or ''}</td>"
        f"<td>{i.prazo or ''}</td><td>{'✅' if i.baixado else '—'}</td></tr>"
        for i in payload.intimacoes)
    total = len(payload.intimacoes)
    baixados = sum(1 for i in payload.intimacoes if i.baixado)
    corpo = f"""<h2>Intimações ESAJ do dia — {datetime.now().strftime('%d/%m/%Y')}</h2>
    <p><b>{total}</b> intimação(ões) na fila · <b>{baixados}</b> com autos baixados.</p>
    <p style="color:#b45309">⚠️ O "receber" (que inicia o prazo) pode exigir certificado — se não recebeu automático, receba manualmente no e-SAJ.</p>
    <table border="1" cellpadding="5" style="border-collapse:collapse">
    <tr><th>Processo</th><th>Classe</th><th>Vara/Foro</th><th>Prazo</th><th>Autos</th></tr>{linhas}</table>"""
    try:
        graph_mail.enviar_email("brunoboiko@gmail.com",
                                f"Intimações ESAJ do dia ({total}) — {datetime.now().strftime('%d/%m')}", corpo)
        email_ok = True
    except Exception:
        email_ok = False
    return {"recebidas": total, "novas": novas, "email_enviado": email_ok}


# REABILITADO 28/07/26: o email do 2FA chega em ipcms@ (remetente saj-envio@tjms,
# assunto "Validação de identificação") e buscar_codigo_2fa extrai OK (testado).
@router.get("/codigo-2fa")
async def codigo_2fa(desde: str = None, _=Depends(verificar_agente)):
    """Retorna o código 2FA do e-SAJ mais recente, ou null.

    O e-SAJ envia o código para a caixa principal do cadastro
    (ESAJ_2FA_MAILBOX, default adm@ipcms.com.br). `desde`: ISO 8601 — só
    códigos após esse instante.
    """
    if not graph_mail.configurado():
        return {"codigo": None, "erro": "Graph não configurado"}
    # tenta várias caixas (o e-SAJ pode mandar p/ adm, ipcms ou bruno) e NUNCA dá 500
    caixas = [
        os.environ.get("ESAJ_2FA_MAILBOX", "adm@ipcms.com.br"),
        os.environ.get("GRAPH_MAILBOX", "ipcms@ipcms.com.br"),
        "ipcms@ipcms.com.br", "adm@ipcms.com.br", "bruno@ipcms.com.br",
    ]
    erro = None
    for caixa in dict.fromkeys([c for c in caixas if c]):
        try:
            codigo = graph_mail.buscar_codigo_2fa(desde_iso=desde, caixa=caixa)
            if codigo:
                return {"codigo": codigo, "caixa": caixa}
        except Exception as e:
            erro = str(e)[:150]
            continue
    return {"codigo": None, "erro": erro}
