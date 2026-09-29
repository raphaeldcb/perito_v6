"""Fila de protocolo — documentos revisados a protocolar (imediato ou em lote).

Fluxo do Bruno: documento pronto (ofício / manifestação do perito / laudo) →
o sistema pergunta se está REVISADO → se sim, protocolar já (imediato) ou
JUNTAR com os outros revisados (lote) e protocolar tudo depois.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean
from .base import Base, TimestampMixin


class ItemProtocolo(Base, TimestampMixin):
    __tablename__ = "item_protocolo"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer)          # processo ligado (opcional)
    cartao_id = Column(Integer)            # cartão do Kanban (opcional)
    numero_processo = Column(String(40))
    tipo_documento = Column(String(30))    # oficio, manifestacao, laudo, outro
    nome_documento = Column(String(255))
    caminho = Column(String(500))          # caminho do .docx gerado (se houver)
    revisado = Column(Boolean, default=True)
    modo = Column(String(10), default="lote")   # imediato | lote
    status = Column(String(20), default="na_fila")  # na_fila, protocolando, protocolado, erro
    protocolo_numero = Column(String(60))  # número real do protocolo (registrado)
    observacao = Column(Text)
