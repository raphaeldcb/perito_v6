#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.services import graph_mail

try:
    print("Buscando em financeiro@ipcms.com.br (nao-lidos)...")

    emails = graph_mail.listar_nao_lidos(limite=100)

    print(f"Total de emails nao-lidos: {len(emails) if emails else 0}")

    encontrado = False
    if emails:
        for email in emails:
            subj = email.get('subject', 'Sem assunto')
            corpo = email.get('bodyPreview', '')

            if '0123456' in subj or '0123456' in corpo:
                print(f"\n✅ ENCONTRADO!")
                print(f"Assunto: {subj}")
                print(f"De: {email.get('from', {}).get('emailAddress', {}).get('address', 'N/A')}")
                print(f"Data: {email.get('receivedDateTime', 'N/A')}")
                encontrado = True
                break

    if not encontrado:
        print(f"\n❌ Email com '0123456' NAO ENCONTRADO")
        print(f"\nUltimos 10 emails:")
        if emails:
            for email in emails[:10]:
                subj = email.get('subject', 'Sem assunto')[:70]
                print(f"  - {subj}")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
