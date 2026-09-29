"""Módulo Engenharia — vistorias de campo (schema-driven).

Um MODELO de vistoria é um schema (JSON) com seções e campos; uma VISTORIA é o
preenchimento desse schema por um engenheiro em campo (funciona offline no PWA e
sincroniza aqui). As fotos e assinaturas ficam em tabelas próprias.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ModeloVistoria(Base, TimestampMixin):
    """Template configurável de vistoria (o construtor edita isto)."""
    __tablename__ = "modelo_vistoria"

    id = Column(Integer, primary_key=True)
    area = Column(String(50), nullable=False, default="engenharia")  # engenharia, elétrica, rural...
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    versao = Column(Integer, nullable=False, default=1)
    # schema = {"secoes": [{"titulo": str, "campos": [ {key,label,tipo,...} ]}]}
    schema = Column(JSON, nullable=False, default=dict)
    icone = Column(String(50), default="📋")
    cor = Column(String(20), default="#2563eb")
    ativo = Column(Boolean, nullable=False, default=True)

    vistorias = relationship("Vistoria", back_populates="modelo")


class Vistoria(Base, TimestampMixin):
    """Preenchimento de um modelo em campo."""
    __tablename__ = "vistoria"

    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey("modelo_vistoria.id"), nullable=False)
    modelo_versao = Column(Integer, nullable=False, default=1)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=True)  # vínculo p/ o laudo
    engenheiro_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    local = Column(String(255))
    gps = Column(String(80))            # "lat,long"
    status = Column(String(20), nullable=False, default="rascunho")  # rascunho | enviada

    # respostas do formulário (espelham as keys do schema do modelo)
    dados = Column(JSON, nullable=False, default=dict)

    # controle de sincronização offline
    uuid_offline = Column(String(64), unique=True, index=True)  # id gerado no dispositivo
    criado_offline_em = Column(String(40))
    sincronizado_em = Column(String(40))

    pdf_path = Column(String(500))
    laudo_rascunho = Column(Text)       # texto gerado pelo Qwen a partir dos campos (fase 1.b)

    modelo = relationship("ModeloVistoria", back_populates="vistorias")
    fotos = relationship("VistoriaFoto", back_populates="vistoria", cascade="all, delete-orphan")
    assinaturas = relationship("VistoriaAssinatura", back_populates="vistoria", cascade="all, delete-orphan")


class VistoriaFoto(Base, TimestampMixin):
    __tablename__ = "vistoria_foto"

    id = Column(Integer, primary_key=True)
    vistoria_id = Column(Integer, ForeignKey("vistoria.id"), nullable=False)
    campo_key = Column(String(80))       # slot do schema (ex.: "foto_fachada"); nulo = acessória
    obrigatoria = Column(Boolean, default=False)
    legenda = Column(String(255))
    arquivo_path = Column(String(500))
    ordem = Column(Integer, default=0)

    vistoria = relationship("Vistoria", back_populates="fotos")


class VistoriaAssinatura(Base, TimestampMixin):
    __tablename__ = "vistoria_assinatura"

    id = Column(Integer, primary_key=True)
    vistoria_id = Column(Integer, ForeignKey("vistoria.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    documento = Column(String(40))       # CPF/RG
    papel = Column(String(50), default="acompanhante")  # acompanhante | engenheiro | proprietário
    imagem_path = Column(String(500))    # assinatura desenhada (PNG base64 salvo em arquivo)

    vistoria = relationship("Vistoria", back_populates="assinaturas")
