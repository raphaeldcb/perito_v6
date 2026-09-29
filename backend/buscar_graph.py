#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.services.graph_mail import GraphMailService

try:
    service = GraphMailService()
    print("Buscando em financeiro@ipcms.com.br...")

    # Busca por número de processo
    emails = service.listar_nao_lidos(mailbox='financeiro@ipcms.com.br', limite=100)

    print(f"\nTotal de emails não-lidos: {len(emails) if emails else 0}")

    encontrado = False
    if emails:
        for email in emails:
            subj = email.get('subject', 'Sem assunto')
            corpo = email.get('body', {}).get('content', '')

            if '0123456' in subj or '0123456' in corpo:
                print(f"\n✅ ENCONTRADO!")
                print(f"Assunto: {subj}")
                print(f"De: {email.get('from', {}).get('emailAddress', {}).get('address', 'N/A')}")
                print(f"Data: {email.get('receivedDateTime', 'N/A')}")
                encontrado = True
                break

    if not encontrado:
        print("\n❌ Email com '0123456' NÃO ENCONTRADO em não-lidos")
        print("\nUltimos 5 emails recebidos:")
        if emails:
            for email in emails[:5]:
                subj = email.get('subject', 'Sem assunto')[:60]
                print(f"  - {subj}")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
