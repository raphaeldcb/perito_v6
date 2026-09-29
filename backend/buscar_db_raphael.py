#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.database import SessionLocal
from app.models.comunicacoes import EmailMessage

db = SessionLocal()
try:
    # Busca todos os emails de raphaeldcb@gmail.com
    emails_raphael = db.query(EmailMessage).filter(
        EmailMessage.from_address.like('%raphaeldcb@gmail.com%')
    ).order_by(EmailMessage.received_datetime.desc()).all()

    print(f"Total de emails de raphaeldcb@gmail.com: {len(emails_raphael)}")

    if emails_raphael:
        print("\nTodos os emails deste remetente:")
        for email in emails_raphael:
            subj = email.subject[:80] if email.subject else "Sem assunto"
            print(f"  {subj}")
            print(f"    De: {email.from_address}")
            print(f"    Data: {email.received_datetime}")
            print(f"    Processo: {email.numero_processo or 'N/A'}")
            print(f"    Judicial: {email.is_judicial}")
            print()

            if '0123456' in (email.subject or '') or '0123456' in (email.body_text or ''):
                print(f"  ✅ ESTE CONTEM '0123456'!")
                print()
    else:
        print("❌ Nenhum email de raphaeldcb@gmail.com no banco de dados")

finally:
    db.close()
