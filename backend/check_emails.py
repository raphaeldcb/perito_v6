#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.database import SessionLocal
from app.models.comunicacoes import EmailMessage

db = SessionLocal()
recentes = db.query(EmailMessage).order_by(EmailMessage.received_datetime.desc()).limit(15).all()
print("15 emails mais recentes:")
for c in recentes:
    proc = c.numero_processo or "N/A"
    subj = c.subject[:60] if c.subject else "Sem assunto"
    print(f"{proc} | {subj}")

# Buscar especificamente pelo número ou texto
print("\n--- Buscando pelo processo 0123456-78.2025.8.12.0001 ---")

# Busca no numero_processo (pode estar NULL)
busca1 = db.query(EmailMessage).filter(
    EmailMessage.numero_processo == "0123456-78.2025.8.12.0001"
).all()
print(f"Com numero_processo exato: {len(busca1)}")

# Busca no assunto/corpo
busca2 = db.query(EmailMessage).filter(
    EmailMessage.subject.like("%0123456%")
).all()
print(f"Com '0123456' no assunto: {len(busca2)}")
for c in busca2:
    print(f"  - Judicial: {c.is_judicial} | {c.subject[:70]}")

busca3 = db.query(EmailMessage).filter(
    EmailMessage.body_text.like("%0123456%")
).all()
print(f"Com '0123456' no corpo: {len(busca3)}")

db.close()
