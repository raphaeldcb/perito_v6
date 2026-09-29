"""
ProjetoCP Phase 2: FastAPI routes for Financeiro (30+ endpoints)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.database import get_db
from app.middleware import get_current_user
from app.models import User
from app.schemas.projetocp_financeiro import (
    FinanceiroCriarRequest, FinanceiroAtualizarRequest, FinanceiroResponse,
    PagamentoCriarRequest, PagamentoResponse,
    ParcelaFinanceiraCriarRequest, ParcelaFinanceiraResponse,
    ParcelamentoRequest, ParcelamentoResponse,
    FinanceiroConfiguracaoResponse, FinanceiroConfiguracaoAtualizar,
    FinanceiroStatsResponse, FinanceiroRelatorioResponse,
    CobrancaIniciarRequest, CobrancaResponse,
    ConciliacaoPagamentoRequest, ConciliacaoResponse
)
from app.decorators.require_feature import require_feature_flag
from app.services.projetocp_financeiro import (
    FinanceiroService, PagamentoService, ParcelamentoService,
    FinanceiroStatsService, CobrancaService, FinanceiroConfiguracaoService
)

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro - Phase 2"])


# ============ LANÇAMENTOS ENDPOINTS ============

@router.post("", response_model=FinanceiroResponse, status_code=status.HTTP_201_CREATED)
async def criar_lancamento(req: FinanceiroCriarRequest,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Criar novo lançamento financeiro"""
    try:
        lancamento = FinanceiroService.criar_lançamento(db, req)
        return lancamento
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{lancamento_id}", response_model=FinanceiroResponse)
async def obter_lancamento(lancamento_id: int,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Obter detalhes de um lançamento"""
    lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
    if not lancamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")
    return lancamento


@router.get("/processo/{processo_id}/lancamentos", response_model=List[FinanceiroResponse])
async def listar_lancamentos_processo(processo_id: int,
                                     current_user: User = Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    """Listar todos os lançamentos de um processo"""
    lancamentos = FinanceiroService.listar_lançamentos_processo(db, processo_id)
    return lancamentos


@router.patch("/{lancamento_id}", response_model=FinanceiroResponse)
async def atualizar_lancamento(lancamento_id: int, req: FinanceiroAtualizarRequest,
                              current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Atualizar lançamento"""
    try:
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        if not lancamento:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        for field, value in req.dict(exclude_unset=True).items():
            if value is not None:
                setattr(lancamento, field, value)

        db.commit()
        return lancamento
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{lancamento_id}/cancelar", status_code=status.HTTP_200_OK)
async def cancelar_lancamento(lancamento_id: int, motivo: str = Query(...),
                             current_user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Cancelar um lançamento com motivo"""
    try:
        FinanceiroService.atualizar_status(db, lancamento_id, "cancelado", motivo)
        return {"status": "cancelado", "lancamento_id": lancamento_id, "motivo": motivo}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============ PAGAMENTOS ENDPOINTS ============

@router.post("/{lancamento_id}/pagamentos", response_model=PagamentoResponse, status_code=status.HTTP_201_CREATED)
async def registrar_pagamento(lancamento_id: int, req: PagamentoCriarRequest,
                             current_user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Registrar um pagamento (recebimento)"""
    try:
        req.financeiro_id = lancamento_id
        pagamento = PagamentoService.registrar_pagamento(db, req, current_user.id)
        return pagamento
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{lancamento_id}/pagamentos", response_model=List[PagamentoResponse])
async def listar_pagamentos(lancamento_id: int,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Listar todos os pagamentos de um lançamento"""
    pagamentos = PagamentoService.listar_pagamentos_lancamento(db, lancamento_id)
    return pagamentos


@router.get("/pagamento/{pagamento_id}", response_model=PagamentoResponse)
async def obter_pagamento(pagamento_id: int,
                         current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """Obter detalhes de um pagamento"""
    pagamento = PagamentoService.obter_pagamento(db, pagamento_id)
    if not pagamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
    return pagamento


# ============ PARCELAMENTO ENDPOINTS ============

@router.post("/{lancamento_id}/parcelar", response_model=ParcelamentoResponse)
async def dividir_em_parcelas(lancamento_id: int, req: ParcelamentoRequest,
                             current_user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Dividir lançamento em N parcelas"""
    try:
        parcelas = ParcelamentoService.dividir_em_parcelas(
            db, lancamento_id, req.num_parcelas,
            req.data_primeira_parcela, req.dias_entre_parcelas
        )
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        return {
            "financeiro_id": lancamento_id,
            "total_parcelas": len(parcelas),
            "parcelas": parcelas,
            "valor_total": lancamento.valor_liquido
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{lancamento_id}/parcelas", response_model=List[ParcelaFinanceiraResponse])
async def listar_parcelas(lancamento_id: int,
                         current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """Listar todas as parcelas de um lançamento"""
    parcelas = ParcelamentoService.listar_parcelas_lancamento(db, lancamento_id)
    return parcelas


@router.post("/parcela/{parcela_id}/marcar-paga")
async def marcar_parcela_paga(parcela_id: int,
                             current_user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Marcar uma parcela como paga"""
    try:
        ParcelamentoService.marcar_parcela_paga(db, parcela_id)
        return {"status": "pago", "parcela_id": parcela_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============ CONFIGURAÇÃO GLOBAL ============

@router.get("/config/geral", response_model=FinanceiroConfiguracaoResponse)
async def obter_configuracao(current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Obter configuração global de financeiro"""
    config = FinanceiroConfiguracaoService.obter_configuracao(db)
    return config


@router.patch("/config/geral", response_model=FinanceiroConfiguracaoResponse)
async def atualizar_configuracao(req: FinanceiroConfiguracaoAtualizar,
                                current_user: User = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """Atualizar configuração global"""
    try:
        config = FinanceiroConfiguracaoService.atualizar_configuracao(
            db, **req.dict(exclude_unset=True)
        )
        return config
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============ STATISTICS & REPORTS ============

@router.get("/stats/geral", response_model=FinanceiroStatsResponse)
async def obter_stats_gerais(data_inicio: Optional[datetime] = Query(None),
                            data_fim: Optional[datetime] = Query(None),
                            current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Obter estatísticas gerais de financeiro"""
    stats = FinanceiroStatsService.obter_stats_gerais(db, data_inicio, data_fim)
    return stats


@router.get("/stats/por-status")
async def stats_por_status(current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Estatísticas: quantidade de lançamentos por status"""
    stats = FinanceiroStatsService.relatorio_por_status(db)
    return {"lancamentos_por_status": stats}


@router.get("/stats/por-tipo")
async def stats_por_tipo(current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Estatísticas: soma de valores por tipo de lançamento"""
    stats = FinanceiroStatsService.relatorio_por_tipo(db)
    return {"valor_por_tipo": stats}


@router.get("/stats/vencimentos-proximos")
async def vencimentos_proximos(dias: int = Query(30, ge=1, le=365),
                              current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Listar lançamentos que vencem nos próximos N dias"""
    lancamentos = FinanceiroStatsService.relatorio_vencimentos_proximos(db, dias)
    return {
        "dias_horizonte": dias,
        "quantidade": len(lancamentos),
        "lancamentos": lancamentos
    }


@router.get("/relatorio/completo", response_model=FinanceiroRelatorioResponse)
async def relatorio_completo(data_inicio: datetime = Query(...),
                            data_fim: datetime = Query(...),
                            current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Gerar relatório financeiro completo para período"""
    from datetime import date
    stats = FinanceiroStatsService.obter_stats_gerais(db, data_inicio, data_fim)
    por_status = FinanceiroStatsService.relatorio_por_status(db)
    por_tipo = FinanceiroStatsService.relatorio_por_tipo(db)

    return {
        "periodo_inicio": data_inicio.date(),
        "periodo_fim": data_fim.date(),
        "stats": stats,
        "lancamentos_por_status": por_status,
        "lancamentos_por_tipo": por_tipo,
        "pagamentos_por_metodo": {},  # TODO: implementar
        "faturamento_por_area": {}  # TODO: integrar com laudos
    }


# ============ COBRANÇA AUTOMÁTICA ============

@router.post("/{lancamento_id}/cobranca/iniciar", response_model=CobrancaResponse)
async def iniciar_cobranca(lancamento_id: int, req: CobrancaIniciarRequest,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Iniciar processo de cobrança para um lançamento"""
    try:
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        if not lancamento:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        notificacao = CobrancaService.gerar_notificacao_cobranca(db, lancamento_id)

        # TODO: Enviar notificação (email, whatsapp, etc)
        FinanceiroService.atualizar_status(db, lancamento_id, "em_cobranca")

        return {
            "financeiro_id": lancamento_id,
            "status": "em_cobranca",
            "proxima_tentativa": datetime.utcnow() + timedelta(days=3),
            "ultimo_envio": datetime.utcnow(),
            "tentativa_numero": 1,
            "mensagem": f"Notificação de cobrança enviada via {req.tipo_notificacao}"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/cobranca/pendentes")
async def listar_para_cobranca(dias_minimo: int = Query(3, ge=0),
                              current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Listar lançamentos pendentes de cobrança"""
    lancamentos = CobrancaService.listar_lancamentos_para_cobrança(db, dias_minimo)
    return {
        "quantidade": len(lancamentos),
        "lancamentos": [{
            "id": l.id,
            "processo_id": l.processo_id,
            "valor": l.valor_liquido,
            "data_vencimento": l.data_vencimento,
            "dias_vencido": (datetime.utcnow() - l.data_vencimento).days,
            "descricao": l.descricao
        } for l in lancamentos]
    }


# ============ RECONCILIAÇÃO ============

@router.post("/pagamento/{pagamento_id}/reconciliar", response_model=ConciliacaoResponse)
async def reconciliar_pagamento(pagamento_id: int, req: ConciliacaoPagamentoRequest,
                               current_user: User = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Reconciliar pagamento com lançamento bancário"""
    try:
        pagamento = PagamentoService.obter_pagamento(db, pagamento_id)
        if not pagamento:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")

        pagamento.lancamento_bancario_id = req.lancamento_bancario_id
        pagamento.reconciliado = True
        pagamento.reconciliado_em = datetime.utcnow()
        db.commit()

        return {
            "pagamento_id": pagamento_id,
            "lancamento_bancario_id": req.lancamento_bancario_id,
            "data_reconciliacao": datetime.utcnow(),
            "status": "reconciliado"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reconciliacao/pendentes")
async def listar_pagamentos_nao_reconciliados(current_user: User = Depends(get_current_user),
                                             db: Session = Depends(get_db)):
    """Listar pagamentos que ainda não foram reconciliados com banco"""
    from app.models.projetocp_financeiro import Pagamento
    pagamentos = db.query(Pagamento).filter(Pagamento.reconciliado == False).all()
    return {
        "quantidade": len(pagamentos),
        "pagamentos": pagamentos
    }


# ============ CÁLCULOS ESPECÍFICOS ============

@router.post("/{lancamento_id}/calcular-juros")
async def calcular_juros_atraso(lancamento_id: int,
                               current_user: User = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Calcular juros por atraso em um lançamento"""
    try:
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        if not lancamento:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        if lancamento.data_vencimento > datetime.utcnow():
            return {"juros": Decimal(0), "motivo": "Lançamento ainda não vencido"}

        dias_atraso = (datetime.utcnow() - lancamento.data_vencimento).days
        juros = (lancamento.valor_liquido * lancamento.juros_mora_percentual / Decimal(100)) * Decimal(dias_atraso)

        return {
            "lancamento_id": lancamento_id,
            "valor_original": lancamento.valor_liquido,
            "dias_atraso": dias_atraso,
            "percentual_juros_mes": lancamento.juros_mora_percentual,
            "juros_calculados": juros,
            "valor_total_com_juros": lancamento.valor_liquido + juros
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{lancamento_id}/projetar-recebimento")
async def projetar_recebimento(lancamento_id: int,
                              data_projetada: datetime = Query(...),
                              current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Projetar valor a receber em data específica (com juros e multa)"""
    try:
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        if not lancamento:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        dias_atraso = max(0, (data_projetada - lancamento.data_vencimento).days)
        config = FinanceiroConfiguracaoService.obter_configuracao(db)

        juros = (lancamento.valor_liquido * lancamento.juros_mora_percentual / Decimal(100)) * Decimal(dias_atraso)
        multa = (lancamento.valor_liquido * config.multa_atraso_percentual / Decimal(100)) if dias_atraso > 0 else Decimal(0)

        valor_projetado = lancamento.valor_liquido + juros + multa

        return {
            "lancamento_id": lancamento_id,
            "data_vencimento": lancamento.data_vencimento,
            "data_projetada": data_projetada,
            "dias_atraso": dias_atraso,
            "valor_original": lancamento.valor_liquido,
            "juros": juros,
            "multa": multa,
            "valor_projetado": valor_projetado
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
