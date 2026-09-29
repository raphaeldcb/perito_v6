"""Camada genérica de ingestão de processos de sistemas externos.

Regra central: upsert por (source_system, external_id) quando houver
external_id; senão por numero_cnj. Re-executar uma importação ATUALIZA os
registros existentes em vez de duplicar — obrigatório para re-sync do
Projuris e re-envio de CSV corrigido.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Processo

CAMPOS_PROCESSO = [
    "numero_cnj", "titulo", "descricao", "autor", "reu", "vara",
    "tribunal", "juiz", "especialidade", "status", "external_id",
]


def upsert_processo(db: Session, dados: dict, source_system: str) -> tuple[Processo, bool]:
    """Retorna (processo, criado). Não faz commit — o chamador controla a transação."""
    numero_cnj = (dados.get("numero_cnj") or "").strip()
    external_id = (dados.get("external_id") or "").strip() or None

    if not numero_cnj and not external_id:
        raise ValueError("Registro sem numero_cnj e sem external_id — impossível reconciliar")

    processo = None
    if external_id:
        processo = (
            db.query(Processo)
            .filter(Processo.source_system == source_system, Processo.external_id == external_id)
            .first()
        )
    if not processo and numero_cnj:
        processo = db.query(Processo).filter(Processo.numero_cnj == numero_cnj).first()

    criado = processo is None
    if criado:
        if not numero_cnj:
            raise ValueError(f"Registro novo (external_id={external_id}) sem numero_cnj")
        processo = Processo(numero_cnj=numero_cnj, source_system=source_system)
        db.add(processo)

    for campo in CAMPOS_PROCESSO:
        valor = dados.get(campo)
        if valor is not None and str(valor).strip() != "":
            setattr(processo, campo, str(valor).strip())

    if external_id:
        processo.external_id = external_id
        processo.source_system = source_system

    data_nomeacao = dados.get("data_nomeacao")
    if data_nomeacao:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                processo.data_nomeacao = datetime.strptime(str(data_nomeacao).strip()[:19], fmt)
                break
            except ValueError:
                continue

    return processo, criado
