from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index, Numeric, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    area = Column(String(40))     # DNA, Contábil, Engenharia, Grafotécnica, Multidisciplinar, Declina
    nivel = Column(String(20))    # especialista, coordenador, master
    # P2 Expiração: ativado quando migração no VPS estiver sincronizada
    # password_expires_at = Column(DateTime, nullable=True)  # Data de expiração da senha (90d)
    # last_coleta_date = Column(DateTime, nullable=True)  # Última data de coleta (Coletador)
    # dias_inatividade = Column(Integer, default=0)  # Dias sem login/coleta

    # AssistProduction ↔ Financeiro: vínculo do colaborador com o device
    # monitorado + base de cálculo do custo_hora (salário OU honorário mensal;
    # quem cadastra decide qual se aplica — custo_hora usa o que estiver preenchido).
    device_id = Column(String(100), unique=True, nullable=True, index=True)
    salario_mensal = Column(Numeric(10, 2), nullable=True)
    honorario_mensal = Column(Numeric(10, 2), nullable=True)

    role = relationship("Role", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"

    __table_args__ = (
        Index("idx_usuario_email", "email"),
    )
