"""Relatório diário por email — pendências, atrasos e estado das filas.

Enviado 1x por dia (REPORT_HORA, default 8h) para REPORT_TO
(por ora somente bruno@ipcms.com.br, a pedido). Marcador em /data evita
reenvio no mesmo dia.
"""
import logging
import os
from datetime import datetime

from app.config import settings
from app.models import Intimacao, Job, KanbanCartao
from app.services import graph_mail
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)

REPORT_TO = os.environ.get("REPORT_TO", "bruno@ipcms.com.br")
REPORT_HORA = int(os.environ.get("REPORT_HORA", "8"))


def _marcador() -> str:
    return os.path.join(settings.storage_dir, "ultimo_relatorio.txt")


def _ja_enviado_hoje() -> bool:
    try:
        with open(_marcador()) as f:
            return f.read().strip() == datetime.now().strftime("%Y-%m-%d")
    except FileNotFoundError:
        return False


def _registrar_envio() -> None:
    os.makedirs(settings.storage_dir, exist_ok=True)
    with open(_marcador(), "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))


def enviar_relatorio_diario() -> bool:
    """Envia o resumo se for hora e ainda não foi enviado hoje."""
    if not graph_mail.configurado():
        return False
    if datetime.now().hour < REPORT_HORA or _ja_enviado_hoje():
        return False

    db = SessionLocal()
    try:
        pendentes = db.query(Intimacao).filter(Intimacao.status == "pendente").count()
        processando = db.query(Intimacao).filter(Intimacao.status == "processando").count()
        erros = db.query(Intimacao).filter(Intimacao.status == "erro").count()
        analisadas = db.query(Intimacao).filter(Intimacao.status == "analisada").count()
        jobs_fila = db.query(Job).filter(Job.status == "na_fila").count()
        jobs_erro = db.query(Job).filter(Job.status == "erro").count()
        aguardando_protocolo = (
            db.query(KanbanCartao)
            .filter(KanbanCartao.status_revisao == "aguardando_protocolo")
            .count()
        )

        ultimas_erro = (
            db.query(Intimacao)
            .filter(Intimacao.status == "erro")
            .order_by(Intimacao.id.desc())
            .limit(5)
            .all()
        )
        detalhe_erros = "".join(
            f"<li>#{i.id} — {(i.assunto or '')[:80]} — <i>{(i.erros or '')[:150]}</i></li>"
            for i in ultimas_erro
        ) or "<li>nenhum</li>"

        alerta = " ⚠️" if (erros or jobs_erro or aguardando_protocolo) else ""
        corpo = f"""
        <h2>Perito v6 — Relatório diário{alerta}</h2>
        <ul>
          <li><b>Intimações pendentes:</b> {pendentes}</li>
          <li><b>Em análise (fila IA):</b> {processando}</li>
          <li><b>Analisadas (total):</b> {analisadas}</li>
          <li><b>Com erro:</b> {erros}</li>
          <li><b>Jobs na fila (ESAJ/IA/protocolo):</b> {jobs_fila}</li>
          <li><b>Jobs com erro definitivo:</b> {jobs_erro}</li>
          <li><b>Laudos aguardando protocolo manual:</b> {aguardando_protocolo}</li>
        </ul>
        <h3>Últimos erros</h3>
        <ul>{detalhe_erros}</ul>
        <p style="color:#888">Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')} — sistema.ipcms.com.br</p>
        """
        graph_mail.enviar_email(
            REPORT_TO,
            f"[Perito v6] Relatório diário{alerta} — {pendentes} pendentes, {erros} erros",
            corpo,
        )
        _registrar_envio()
        return True
    finally:
        db.close()
