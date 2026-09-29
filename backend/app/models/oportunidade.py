"""Oportunidade de captação — lead de perícia achado no Diário e analisado pelo Qwen.

Tabela NOVA (aditiva). Guarda a análise prévia de mérito e a qualidade do lead
(advogado, se é defensoria/empresa grande) para ranquear quem tem "bala na agulha".
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean
from .base import Base, TimestampMixin


class Oportunidade(Base, TimestampMixin):
    __tablename__ = "oportunidade"

    id = Column(Integer, primary_key=True)
    djen_id = Column(String(60), unique=True)   # dedup pela publicação
    tribunal = Column(String(20))
    numero_processo = Column(String(40))
    area = Column(String(60))                    # área de perícia (DNA, contábil...)
    oportunidade = Column(Boolean, default=True) # é lead de perícia?
    # qualidade do lead
    defensoria = Column(Boolean, default=False)
    empresa_grande = Column(Boolean, default=False)
    oab_antiga = Column(Boolean, default=False)
    advogado_nome = Column(String(160))
    advogado_oab = Column(String(30))
    advogado_email = Column(String(160))   # extraído (publicação/rodapé/autos)
    # análise de mérito (prévia — sem garantir resultado)
    merito_sem_pct = Column(Numeric(5, 2))
    merito_com_pct = Column(Numeric(5, 2))
    ressalvas = Column(Text)
    resumo = Column(Text)
    score = Column(Numeric(6, 2))                # ranking (maior = melhor lead)
    status = Column(String(20), default="novo")  # novo, contatado, descartado
    email_rascunho = Column(Text)                # preenchido por último (Qwen)
    texto = Column(Text)
    link = Column(String(500))
