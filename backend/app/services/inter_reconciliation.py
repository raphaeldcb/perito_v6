"""Reconciliação Inter ↔ Perito — Auto-match transações com lançamento_bancario."""
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)


def reconciliar_transacao_inter(
    db: Session,
    inter_id: str,
    valor: float,
    data: str,
    descricao: str,
    tipo_transacao: str,  # "credito" ou "debito"
    conta_inter_id: int,
) -> dict:
    """Tenta auto-reconciliar transação da Inter com lançamento_bancario.

    Estratégia de match:
    1. Procura exato: inter_id já existe? → skip (duplicada)
    2. Procura por valor + data (±2 dias): encontrou único match? → linká
    3. Não encontrou: cria novo InterTransaction + fica pendente pra review manual

    Retorna: {ok, matched, lancamento_id_se_matched, inter_transaction_id}
    """
    from app.models.inter import InterTransaction
    from app.models.financeiro import LancamentoBancario

    try:
        # 1. Checar se já existe (evitar duplicata)
        existe = db.query(InterTransaction).filter(
            InterTransaction.inter_id == inter_id
        ).first()

        if existe:
            return {"ok": True, "matched": False, "motivo": "Já processado", "inter_transaction_id": existe.id}

        # 2. Buscar lançamento_bancario por valor + data (±2 dias)
        data_obj = datetime.fromisoformat(data.replace("Z", "+00:00")).date() if isinstance(data, str) else data
        from datetime import timedelta

        lancamento = db.query(LancamentoBancario).filter(
            and_(
                LancamentoBancario.valor == Decimal(str(valor)),
                LancamentoBancario.data >= data_obj - timedelta(days=2),
                LancamentoBancario.data <= data_obj + timedelta(days=2),
                LancamentoBancario.status == "pendente",  # Só match com pendentes
            )
        ).first()

        # 3. Criar InterTransaction (novo ou ligado)
        txn = InterTransaction(
            conta_id=conta_inter_id,
            inter_id=inter_id,
            tipo=tipo_transacao,
            data=data_obj,
            descricao=descricao,
            valor=Decimal(str(valor)),
            status="confirmado",
            reconciliado=bool(lancamento),
            lancamento_id=lancamento.id if lancamento else None,
        )

        db.add(txn)

        # 4. Se achou match, marcar lançamento como conciliado
        if lancamento:
            lancamento.status = "conciliado"
            lancamento.coletador_id = None  # Inter é automático, não precisa coletador

        db.commit()
        db.refresh(txn)

        return {
            "ok": True,
            "matched": bool(lancamento),
            "inter_transaction_id": txn.id,
            "lancamento_id": lancamento.id if lancamento else None,
            "motivo": "Match automático" if lancamento else "Pendente revisão manual",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Reconciliation error: {str(e)}")
        return {"ok": False, "erro": str(e)}


def sincronizar_extrato_completo(
    db: Session,
    conta_inter_id: int,
    extrato_json: dict,
) -> dict:
    """Sincroniza extrato completo (via GET /extrato) — reconcilia todas as txns.

    Usado em: startup (catch-up) ou manual refresh
    """
    from app.models.inter import InterTransaction
    from app.models.financeiro import LancamentoBancario

    total_processadas = 0
    total_reconciliadas = 0
    erros = []

    try:
        dados = extrato_json.get("dadosExtrato", {})
        movimentacoes = dados.get("movimentacoes", [])

        for mov in movimentacoes:
            inter_id = mov.get("id")
            valor = abs(float(mov.get("valor", 0)))
            data = mov.get("data")
            descricao = mov.get("descricao", "")
            tipo = "credito" if float(mov.get("valor", 0)) > 0 else "debito"

            resultado = reconciliar_transacao_inter(
                db, inter_id, valor, data, descricao, tipo, conta_inter_id
            )

            if resultado["ok"]:
                total_processadas += 1
                if resultado.get("matched"):
                    total_reconciliadas += 1
            else:
                erros.append(f"{inter_id}: {resultado.get('erro')}")

        return {
            "ok": True,
            "total_movimentacoes": len(movimentacoes),
            "processadas": total_processadas,
            "reconciliadas": total_reconciliadas,
            "pendente_manual": total_processadas - total_reconciliadas,
            "erros": erros,
        }

    except Exception as e:
        logger.error(f"Sincronização extrato error: {str(e)}")
        return {"ok": False, "erro": str(e)}
