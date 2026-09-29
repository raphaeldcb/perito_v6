#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.database import SessionLocal
from app.models.comunicacoes import EmailMessage
from sqlalchemy import func, distinct

db = SessionLocal()
try:
    total = db.query(EmailMessage).count()
    print(f"Total de emails no BD: {total}")

    # Agrupa por remetente
    remetentes = db.query(
        EmailMessage.from_address,
        func.count(EmailMessage.id).label('qtd')
    ).group_by(EmailMessage.from_address).order_by(
        func.count(EmailMessage.id).desc()
    ).limit(15).all()

    print(f"\nTop 15 remetentes:")
    for remetente, qtd in remetentes:
        print(f"  {qtd:3d}x {remetente}")

    # Busca especificamente por raphael
    print(f"\n--- Buscando variantes de 'raphael' ---")
    from_raphaels = db.query(distinct(EmailMessage.from_address)).filter(
        EmailMessage.from_address.ilike('%raphael%')
    ).all()

    if from_raphaels:
        print(f"Encontrado:")
        for (addr,) in from_raphaels:
            print(f"  - {addr}")
    else:
        print("Nada encontrado com 'raphael'")

finally:
    db.close()
