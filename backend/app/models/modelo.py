"""Modelos de documentos (ofícios, laudos, propostas) do Bruno.

Os arquivos ficam na pasta MODELOS do OneDrive (nuvem). O agente Mac sincroniza
a LISTA para o sistema; depois marcamos os campos preenchíveis em cada um.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Index
from app.models.types import JSONBType
from .base import Base, TimestampMixin


class Modelo(Base, TimestampMixin):
    __tablename__ = "modelo"

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    caminho_relativo = Column(String(500), unique=True, nullable=False)  # dentro de MODELOS
    pasta = Column(String(200))          # subpasta (Laudos, Contratos, DNA...)
    tipo = Column(String(20))            # docx, pdf, xlsx
    categoria = Column(String(40))       # oficio, laudo, proposta, contrato, tabela, outro
    campos = Column(JSONBType)               # campos preenchíveis identificados (fase futura)
    ativo = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_modelo_categoria", "categoria"),
    )
