"""Nota Fiscal de Serviço (NFSe) por perícia — prefeitura de Campo Grande (DSF).

Cada perícia (Processo) pode gerar UMA nota ativa. O sistema confere antes de
emitir e não duplica. A emissão real no webservice DSF fica atrás da flag
NFSE_EMISSAO_ATIVA (default OFF) — Campo Grande não tem homologação, então
nada é emitido de verdade até validação.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class NotaFiscal(Base, TimestampMixin):
    __tablename__ = "nota_fiscal"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=True)  # a perícia
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)    # prestador (IPC)

    # Numeração
    numero_rps = Column(String(30))     # Recibo Provisório de Serviços (gerado antes)
    serie_rps = Column(String(10), default="1")
    numero_nfse = Column(String(30))    # número oficial devolvido pela prefeitura
    codigo_verificacao = Column(String(60))

    # Tomador (cliente que paga a perícia) — endereço obrigatório no DSF
    tomador_nome = Column(String(200))
    tomador_documento = Column(String(20))   # CPF/CNPJ
    tomador_email = Column(String(200))
    tomador_logradouro = Column(String(120))
    tomador_numero = Column(String(20))
    tomador_bairro = Column(String(80))
    tomador_cidade = Column(String(80))
    tomador_uf = Column(String(2))
    tomador_cep = Column(String(10))
    tomador_telefone = Column(String(30))

    # Serviço
    discriminacao = Column(Text)             # descrição do serviço pericial
    valor_servico = Column(Numeric(12, 2))
    aliquota_iss = Column(Numeric(5, 2))
    codigo_servico = Column(String(20))      # item da lista de serviços do município
    competencia = Column(String(7))          # "2026-07"

    status = Column(String(20), nullable=False, default="rascunho")
    # rascunho, emitida, erro, cancelada
    erro = Column(Text)
    xml_path = Column(String(500))           # XML assinado/retornado
    pdf_path = Column(String(500))           # DANFSE
    data_emissao = Column(DateTime)
    # cert_id_usado removido — não existe no banco (será adicionado em migration se necessário)

    # Origem (para o gatilho automático a partir do recebimento)
    lancamento_id = Column(Integer, ForeignKey("lancamento_bancario.id"), nullable=True)

    processo = relationship("Processo")

    __table_args__ = (
        # Dedup: no máximo uma nota NÃO-cancelada por perícia (garantido em código)
        Index("idx_nota_processo", "processo_id"),
        Index("idx_nota_status", "status"),
        Index("idx_nota_competencia", "competencia"),
    )
