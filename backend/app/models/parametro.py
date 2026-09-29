"""Parâmetros do sistema editáveis pelo admin (sem precisar codar).

Categorias: credenciais (logins/senhas de tribunais), urls (sites ESAJ/eproc/
PJe/NFe...), caminhos (diretórios de modelos, laudos, destino...), valores
(tabela de honorários), sistema (mapeamentos internos).
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Index
from .base import Base, TimestampMixin


class Parametro(Base, TimestampMixin):
    __tablename__ = "parametro"

    id = Column(Integer, primary_key=True)
    chave = Column(String(100), unique=True, nullable=False)  # ex: esaj_tjms_senha
    valor = Column(Text, default="")
    categoria = Column(String(50), nullable=False, default="sistema")
    descricao = Column(String(300))
    secreto = Column(Boolean, nullable=False, default=False)  # mascara na UI
    tipo = Column(String(20), nullable=False, default="texto")  # texto|senha|url|caminho|valor

    __table_args__ = (
        Index("idx_parametro_categoria", "categoria"),
    )
