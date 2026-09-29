"""Histórico do juiz para o motor de honorários — decide ratifica × declina.

Acumula o comportamento de cada juízo (homologa? paga? reduz? quanto?) para o
motor decidir se vale a pena ratificar os honorários ou declinar o encargo.
Tabela NOVA (create_all cria; não altera tabelas existentes)."""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text, DateTime
from datetime import datetime

from app.models.base import Base, TimestampMixin


class HistoricoJuiz(Base, TimestampMixin):
    __tablename__ = "historico_juiz"

    id = Column(Integer, primary_key=True)
    juiz_slug = Column(String(200), unique=True, index=True)  # nome normalizado (chave)
    juiz_nome = Column(String(200))
    comarca = Column(String(120))
    vara = Column(String(120))

    total_atuacoes = Column(Integer, default=0)
    homologou = Column(Integer, default=0)        # nº de vezes que homologou os trabalhos
    reduziu = Column(Integer, default=0)          # nº de vezes que reduziu honorários
    declinamos = Column(Integer, default=0)       # nº de vezes que declinamos deste juízo
    reducao_media_pct = Column(Numeric(5, 2))     # média das reduções (%)
    nunca_paga = Column(Boolean, default=False)   # marca manual/aprendida: juízo que não paga
    ultima_atuacao = Column(DateTime, default=datetime.utcnow)
    obs = Column(Text)
