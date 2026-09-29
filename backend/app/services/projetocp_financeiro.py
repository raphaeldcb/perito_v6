"""
ProjetoCP Phase 2: Services for Financial operations
Cálculo de juros, parcelamento, cobrança, stats
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.projetocp_financeiro import (
    Financeiro, Pagamento, ParcelaFinanceira, FinanceiroConfiguracao,
    FinanceiroStatus, FinanceiroTipo
)
from app.models.processo import Processo
from app.schemas.projetocp_financeiro import (
    FinanceiroCriarRequest, PagamentoCriarRequest, ParcelamentoRequest
)

logger = logging.getLogger(__name__)


class FinanceiroService:
    """Serviço de gerenciamento de lançamentos financeiros"""

    @staticmethod
    def criar_lançamento(db: Session, dados: FinanceiroCriarRequest) -> Financeiro:
        """Criar novo lançamento financeiro"""
        valor_liquido = dados.valor_bruto - dados.valor_desconto

        lancamento = Financeiro(
            processo_id=dados.processo_id,
            laudo_id=dados.laudo_id,
            tipo=dados.tipo.value if hasattr(dados.tipo, 'value') else dados.tipo,
            descricao=dados.descricao,
            valor_bruto=dados.valor_bruto,
            valor_desconto=dados.valor_desconto,
            valor_liquido=valor_liquido,
            moeda=dados.moeda,
            data_vencimento=dados.data_vencimento,
            indexador=dados.indexador,
            juros_mora_percentual=dados.juros_mora_percentual,
            numero_nfse=dados.numero_nfse,
            numero_rps=dados.numero_rps,
            referencia_externa=dados.referencia_externa,
            metadata=dados.metadata,
            status="pendente"
        )

        db.add(lancamento)
        db.commit()
        logger.info(f"Lançamento financeiro criado: {lancamento.id} (R$ {valor_liquido})")
        return lancamento

    @staticmethod
    def obter_lançamento(db: Session, lancamento_id: int) -> Optional[Financeiro]:
        """Obter um lançamento por ID"""
        return db.query(Financeiro).filter(Financeiro.id == lancamento_id).first()

    @staticmethod
    def listar_lançamentos_processo(db: Session, processo_id: int) -> List[Financeiro]:
        """Listar todos os lançamentos de um processo"""
        return db.query(Financeiro).filter(
            Financeiro.processo_id == processo_id
        ).order_by(Financeiro.data_vencimento).all()

    @staticmethod
    def listar_lançamentos_status(db: Session, status: str, limite: int = 100) -> List[Financeiro]:
        """Listar lançamentos com status específico"""
        return db.query(Financeiro).filter(
            Financeiro.status == status
        ).order_by(Financeiro.data_vencimento).limit(limite).all()

    @staticmethod
    def atualizar_status(db: Session, lancamento_id: int, novo_status: str, motivo: Optional[str] = None):
        """Atualizar status de um lançamento"""
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        if not lancamento:
            raise ValueError(f"Lançamento {lancamento_id} não encontrado")

        lancamento.status = novo_status
        if motivo and novo_status == "cancelado":
            lancamento.motivo_cancelamento = motivo

        db.commit()
        logger.info(f"Lançamento {lancamento_id} status atualizado para: {novo_status}")

    @staticmethod
    def calcular_total_recebido(db: Session, lancamento_id: int) -> Decimal:
        """Calcular total recebido em um lançamento (soma de pagamentos)"""
        total = db.query(func.sum(Pagamento.valor_recebido)).filter(
            Pagamento.financeiro_id == lancamento_id,
            Pagamento.em_custódia == False  # Só contar efetivamente recebido
        ).scalar()
        return total or Decimal(0)

    @staticmethod
    def atualizar_status_baseado_pagamento(db: Session, lancamento_id: int):
        """Atualizar status do lançamento baseado no que foi recebido (XOR logic)"""
        lancamento = FinanceiroService.obter_lançamento(db, lancamento_id)
        if not lancamento:
            return

        total_recebido = FinanceiroService.calcular_total_recebido(db, lancamento_id)

        if lancamento.status == "cancelado":
            return  # Não alterar cancelado

        if total_recebido >= lancamento.valor_liquido:
            lancamento.status = "pago"
            lancamento.data_primeiro_recebimento = lancamento.data_primeiro_recebimento or datetime.utcnow()
        elif total_recebido > 0:
            lancamento.status = "parcialmente_pago"
        elif lancamento.data_vencimento < datetime.utcnow():
            lancamento.status = "vencido"
        else:
            lancamento.status = "pendente"

        db.commit()


class PagamentoService:
    """Serviço de gerenciamento de pagamentos"""

    @staticmethod
    def registrar_pagamento(db: Session, dados: PagamentoCriarRequest,
                           recebido_por_id: Optional[int] = None) -> Pagamento:
        """Registrar um novo pagamento (recebimento)"""
        lancamento = db.query(Financeiro).filter(Financeiro.id == dados.financeiro_id).first()
        if not lancamento:
            raise ValueError(f"Lançamento {dados.financeiro_id} não encontrado")

        # Determinar número da parcela
        ultimo_pagamento = db.query(Pagamento).filter(
            Pagamento.financeiro_id == dados.financeiro_id
        ).order_by(Pagamento.parcela_numero.desc()).first()

        parcela_numero = (ultimo_pagamento.parcela_numero + 1) if ultimo_pagamento else 1

        pagamento = Pagamento(
            financeiro_id=dados.financeiro_id,
            parcela_numero=parcela_numero,
            data_pagamento=dados.data_pagamento or datetime.utcnow(),
            valor_recebido=dados.valor_recebido,
            metodo_pagamento=dados.metodo_pagamento,
            banco_recebimento=dados.banco_recebimento,
            referencia_banco=dados.referencia_banco,
            comprovante_path=dados.comprovante_path,
            nota=dados.nota,
            recebido_por_id=recebido_por_id
        )

        db.add(pagamento)
        db.flush()

        # Atualizar status do lançamento
        FinanceiroService.atualizar_status_baseado_pagamento(db, dados.financeiro_id)

        db.commit()
        logger.info(f"Pagamento registrado: {pagamento.id} (R$ {dados.valor_recebido})")
        return pagamento

    @staticmethod
    def listar_pagamentos_lancamento(db: Session, lancamento_id: int) -> List[Pagamento]:
        """Listar todos os pagamentos de um lançamento"""
        return db.query(Pagamento).filter(
            Pagamento.financeiro_id == lancamento_id
        ).order_by(Pagamento.data_pagamento).all()

    @staticmethod
    def obter_pagamento(db: Session, pagamento_id: int) -> Optional[Pagamento]:
        """Obter um pagamento por ID"""
        return db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()


class ParcelamentoService:
    """Serviço de divisão em parcelas"""

    @staticmethod
    def dividir_em_parcelas(db: Session, lancamento_id: int, num_parcelas: int,
                           data_primeira_parcela: Optional[datetime] = None,
                           dias_entre_parcelas: int = 30) -> List[ParcelaFinanceira]:
        """Dividir um lançamento em N parcelas"""
        lancamento = db.query(Financeiro).filter(Financeiro.id == lancamento_id).first()
        if not lancamento:
            raise ValueError(f"Lançamento {lancamento_id} não encontrado")

        if num_parcelas < 1 or num_parcelas > 12:
            raise ValueError("Número de parcelas deve estar entre 1 e 12")

        # Calcular valor de cada parcela
        valor_parcela = lancamento.valor_liquido / Decimal(num_parcelas)

        # Data da primeira parcela
        if not data_primeira_parcela:
            data_primeira_parcela = lancamento.data_vencimento

        parcelas_criadas = []
        for i in range(1, num_parcelas + 1):
            data_venc = data_primeira_parcela + timedelta(days=(i - 1) * dias_entre_parcelas)

            # Última parcela pega o resto (para ajustar arredondamentos)
            if i == num_parcelas:
                valor = lancamento.valor_liquido - (valor_parcela * (num_parcelas - 1))
            else:
                valor = valor_parcela

            parcela = ParcelaFinanceira(
                financeiro_id=lancamento_id,
                numero_parcela=i,
                valor_parcela=valor,
                data_vencimento=data_venc,
                status="pendente"
            )
            db.add(parcela)
            parcelas_criadas.append(parcela)

        db.commit()
        logger.info(f"Lançamento {lancamento_id} dividido em {num_parcelas} parcelas")
        return parcelas_criadas

    @staticmethod
    def listar_parcelas_lancamento(db: Session, lancamento_id: int) -> List[ParcelaFinanceira]:
        """Listar todas as parcelas de um lançamento"""
        return db.query(ParcelaFinanceira).filter(
            ParcelaFinanceira.financeiro_id == lancamento_id
        ).order_by(ParcelaFinanceira.numero_parcela).all()

    @staticmethod
    def marcar_parcela_paga(db: Session, parcela_id: int, data_pagamento: Optional[datetime] = None):
        """Marcar uma parcela como paga"""
        parcela = db.query(ParcelaFinanceira).filter(ParcelaFinanceira.id == parcela_id).first()
        if not parcela:
            raise ValueError(f"Parcela {parcela_id} não encontrada")

        parcela.status = "pago"
        parcela.data_pagamento_efetivo = data_pagamento or datetime.utcnow()
        db.commit()

        # Atualizar status do lançamento
        FinanceiroService.atualizar_status_baseado_pagamento(db, parcela.financeiro_id)


class FinanceiroStatsService:
    """Serviço de estatísticas e relatórios financeiros"""

    @staticmethod
    def obter_stats_gerais(db: Session, data_inicio: Optional[datetime] = None,
                          data_fim: Optional[datetime] = None) -> Dict[str, Any]:
        """Obter estatísticas gerais de financeiro"""
        query = db.query(Financeiro)

        if data_inicio:
            query = query.filter(Financeiro.data_emissao >= data_inicio)
        if data_fim:
            query = query.filter(Financeiro.data_emissao <= data_fim)

        lancamentos = query.all()

        total_emitido = sum(l.valor_bruto for l in lancamentos) or Decimal(0)
        total_recebido = sum(
            FinanceiroService.calcular_total_recebido(db, l.id) for l in lancamentos
        ) or Decimal(0)
        total_pendente = total_emitido - total_recebido

        lancamentos_vencidos = [l for l in lancamentos if l.status == "vencido"]
        total_vencido = sum(l.valor_liquido - FinanceiroService.calcular_total_recebido(db, l.id)
                           for l in lancamentos_vencidos) or Decimal(0)

        taxa_recebimento = (total_recebido / total_emitido * 100) if total_emitido > 0 else Decimal(0)

        return {
            "total_emitido": total_emitido,
            "total_recebido": total_recebido,
            "total_pendente": total_pendente,
            "total_vencido": total_vencido,
            "taxa_recebimento": taxa_recebimento,
            "quantidade_processos": db.query(Processo).filter(
                Processo.id.in_([l.processo_id for l in lancamentos])
            ).count() if lancamentos else 0,
            "quantidade_lancamentos": len(lancamentos),
            "quantidade_vencidos": len(lancamentos_vencidos),
            "quantidade_abertos": len([l for l in lancamentos if l.status in ["pendente", "em_cobranca"]]),
        }

    @staticmethod
    def relatorio_por_status(db: Session) -> Dict[str, int]:
        """Contar lançamentos por status"""
        resultados = db.query(
            Financeiro.status,
            func.count(Financeiro.id)
        ).group_by(Financeiro.status).all()

        return {status: count for status, count in resultados}

    @staticmethod
    def relatorio_por_tipo(db: Session) -> Dict[str, Decimal]:
        """Somar valores por tipo de lançamento"""
        resultados = db.query(
            Financeiro.tipo,
            func.sum(Financeiro.valor_liquido)
        ).group_by(Financeiro.tipo).all()

        return {tipo: (valor or Decimal(0)) for tipo, valor in resultados}

    @staticmethod
    def relatorio_vencimentos_proximos(db: Session, dias: int = 30) -> List[Dict[str, Any]]:
        """Listar lançamentos vencidos nos próximos N dias"""
        agora = datetime.utcnow()
        futura = agora + timedelta(days=dias)

        lancamentos = db.query(Financeiro).filter(
            and_(
                Financeiro.data_vencimento >= agora,
                Financeiro.data_vencimento <= futura,
                Financeiro.status.in_(["pendente", "vencido"])
            )
        ).order_by(Financeiro.data_vencimento).all()

        return [{
            "id": l.id,
            "processo_id": l.processo_id,
            "tipo": l.tipo,
            "valor": l.valor_liquido,
            "data_vencimento": l.data_vencimento,
            "dias_ate_vencer": (l.data_vencimento - agora).days,
            "status": l.status
        } for l in lancamentos]


class CobrancaService:
    """Serviço de automação de cobrança"""

    @staticmethod
    def gerar_notificacao_cobranca(db: Session, lancamento_id: int) -> Dict[str, str]:
        """Gerar conteúdo de notificação de cobrança"""
        lancamento = db.query(Financeiro).filter(Financeiro.id == lancamento_id).first()
        if not lancamento:
            raise ValueError(f"Lançamento {lancamento_id} não encontrado")

        dias_vencido = (datetime.utcnow() - lancamento.data_vencimento).days

        return {
            "assunto": f"Cobrança: Lançamento {lancamento_id} vencido há {dias_vencido} dias",
            "corpo": f"""
Prezado Cliente,

Informamos que o lançamento abaixo encontra-se pendente de pagamento:

Descrição: {lancamento.descricao}
Valor: R$ {lancamento.valor_liquido:.2f}
Vencimento: {lancamento.data_vencimento.strftime('%d/%m/%Y')}
Dias vencido: {dias_vencido}

Favor proceder com o pagamento imediatamente para evitar ações judiciais.

Atenciosamente,
IPC - Perícias
            """
        }

    @staticmethod
    def listar_lancamentos_para_cobrança(db: Session, dias_minimo_atraso: int = 3) -> List[Financeiro]:
        """Listar lançamentos que devem entrar em cobrança"""
        data_limite = datetime.utcnow() - timedelta(days=dias_minimo_atraso)

        return db.query(Financeiro).filter(
            and_(
                Financeiro.status.in_(["vencido"]),
                Financeiro.data_vencimento <= data_limite
            )
        ).order_by(Financeiro.data_vencimento).all()


class FinanceiroConfiguracaoService:
    """Serviço de configuração global de financeiro"""

    @staticmethod
    def obter_configuracao(db: Session) -> FinanceiroConfiguracao:
        """Obter configuração global (singleton)"""
        config = db.query(FinanceiroConfiguracao).filter(FinanceiroConfiguracao.id == 1).first()

        if not config:
            config = FinanceiroConfiguracao(id=1)
            db.add(config)
            db.commit()

        return config

    @staticmethod
    def atualizar_configuracao(db: Session, **kwargs) -> FinanceiroConfiguracao:
        """Atualizar configuração global"""
        config = FinanceiroConfiguracaoService.obter_configuracao(db)

        for chave, valor in kwargs.items():
            if hasattr(config, chave):
                setattr(config, chave, valor)

        db.commit()
        logger.info(f"Configuração financeira atualizada")
        return config
