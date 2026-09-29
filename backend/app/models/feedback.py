# app/models/feedback.py
#
# Task 1 do plano de Feedback & Error Reporting System.
#
# ⚠️ DESVIOS DO TEXTO ORIGINAL DO PLANO (ver relatório task-1-report.md):
#   1. `from app.database import Base` — não existe `app/database.py` neste
#      projeto; o Base declarativo mora em `app.models.base` (mesmo import
#      usado por todos os outros models, ex.: app/models/user.py).
#   2. `ForeignKey("users.id")` — a tabela real de usuários é `usuario`
#      (User.__tablename__ = "usuario"), não `users`. Mesmo desvio já
#      documentado em migrations/2026_08_03_calculo_v2_tables.sql.
#   3. `back_populates="feedback_reports"` exigiria adicionar uma
#      relationship em app/models/user.py, o que violaria a instrução
#      explícita desta task ("Do NOT modify existing models"). Usamos
#      `backref="feedback_reports"` em vez de `back_populates` — mesmo
#      efeito bidirecional (User.feedback_reports funciona normalmente
#      na Task 2), sem tocar em user.py.
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    attachment_path = Column(String(500), nullable=True)
    severity = Column(String(20), default="MEDIUM")
    status = Column(String(20), default="PENDING")
    is_in_scope = Column(Boolean, nullable=True)
    analysis_notes = Column(Text, nullable=True)
    implementation_branch = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    analyzed_at = Column(DateTime, nullable=True)
    implemented_at = Column(DateTime, nullable=True)
    created_ip = Column(String(45), nullable=True)

    user = relationship("User", backref="feedback_reports")
    attachments = relationship("FeedbackAttachment", cascade="all, delete-orphan")


class FeedbackAttachment(Base):
    __tablename__ = "feedback_attachments"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback_reports.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
