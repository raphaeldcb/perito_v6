"""Coletadores (conveniados) e seus documentos.

Coletador tem acesso restrito ao próprio portal (role 'coletador'): vê apenas
seus comprovantes de pagamento, o termo de autorização de coleta (preenchível),
contrato, vídeo de treinamento e demais documentos. Sem acesso ao resto.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, Index
from app.models.types import JSONBType
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Coletador(Base, TimestampMixin):
    __tablename__ = "coletador"

    id = Column(Integer, primary_key=True)
    # Código SCPG (sistema de gestão de coletas) — usado para nomear o comprovante
    # como CODIGO.ANO.MES.pdf (ex: 297.26.01.pdf). Vem do ID do CSV.
    codigo_scpg = Column(Integer, index=True)
    # Login por CPF (limpo, 11 dígitos). hashed_password reusa o mesmo hash bcrypt.
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    nome_completo = Column(String(200), nullable=False)
    apelido = Column(String(80))               # usado no match do extrato (ex: "geriel")
    hashed_password = Column(String(255), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    is_prestador = Column(Boolean, default=False)  # também presta serviço (recebe por fora)
    ativo = Column(Boolean, default=True)
    primeiro_acesso = Column(Boolean, default=True)  # força atualização de cadastro no 1º login

    # Cadastro que o coletador preenche no primeiro acesso
    email_pessoal = Column(String(200))
    celular = Column(String(30))
    pix = Column(String(120))
    conta_bancaria = Column(String(120))
    endereco = Column(Text)
    cidade = Column(String(120))
    cep = Column(String(12))

    documentos = relationship("DocumentoColetador", back_populates="coletador", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_coletador_apelido", "apelido"),
    )


class DocumentoColetador(Base, TimestampMixin):
    __tablename__ = "documento_coletador"

    id = Column(Integer, primary_key=True)
    coletador_id = Column(Integer, ForeignKey("coletador.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(40), nullable=False)  # comprovante, termo_autorizacao, contrato, video, outro
    titulo = Column(String(200))
    arquivo_path = Column(String(500))         # PDF/vídeo/etc no storage
    # Termo de autorização é preenchível: os campos ficam aqui e podem ser exportados p/ PDF
    dados_formulario = Column(JSONBType)
    referencia = Column(String(60))            # ex: competência "2026-07" para comprovantes
    valor = Column(Numeric(12, 2))             # valor do comprovante, se aplicável
    enviado_por_coletador = Column(Boolean, default=False)

    coletador = relationship("Coletador", back_populates="documentos")

    __table_args__ = (
        Index("idx_doc_coletador", "coletador_id", "tipo"),
    )
