"""Protocolo de laudos aprovados — via fila de jobs, sem números fabricados.

O protocolo real exige certificado digital (Mac + pipeline v5.3). Este worker
apenas ENFILEIRA: cartões com status 'coordenador_aprovou' viram Job tipo
'protocolo' e mudam para 'aguardando_protocolo'. O número de protocolo só é
gravado quando o mac_agent reporta a submissão real ao tribunal
(ver routes/jobs.py::_aplicar_resultado).
"""
import logging

from app.models import KanbanCartao, Job
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)


def enfileirar_cartoes_aprovados() -> int:
    """Move cartões aprovados para a fila de protocolo. Retorna quantos enfileirou."""
    db = SessionLocal()
    enfileirados = 0
    try:
        aprovados = (
            db.query(KanbanCartao)
            .filter(KanbanCartao.status_revisao == "coordenador_aprovou")
            .all()
        )
        for cartao in aprovados:
            job = Job(
                tipo="protocolo",
                payload={
                    "cartao_id": cartao.id,
                    "titulo": cartao.titulo,
                    "laudo_docx_path": cartao.laudo_docx_path,
                    "numero_cnj": cartao.processo.numero_cnj if cartao.processo else None,
                    "tribunal": cartao.processo.tribunal if cartao.processo else "TJMS",
                },
                status="na_fila",
            )
            db.add(job)
            cartao.status_revisao = "aguardando_protocolo"
            db.commit()
            enfileirados += 1
            logger.info(f"📤 Cartão {cartao.id} ({cartao.titulo!r}) enfileirado para protocolo real")
    finally:
        db.close()
    return enfileirados
