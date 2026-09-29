#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.services import graph_mail

try:
    print("Buscando emails de raphaeldcb@gmail.com em financeiro...")

    token = graph_mail._token()
    headers = {"Authorization": f"Bearer {token}"}

    # Busca ultimos 100 emails (sem filtro, filtra depois em Python)
    url = "https://graph.microsoft.com/v1.0/me/messages"
    params = {"top": 100, "orderby": "receivedDateTime desc"}

    import requests
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()

    all_emails = resp.json().get("value", [])

    # Filtra por remetente
    from_raphael = [e for e in all_emails if "raphaeldcb@gmail.com" in e.get("from", {}).get("emailAddress", {}).get("address", "").lower()]

    print(f"Total de emails de raphaeldcb@gmail.com: {len(from_raphael)}")

    encontrado = False
    if from_raphael:
        print("\nTodos os emails deste remetente:")
        for email in from_raphael:
            subj = email.get('subject', 'Sem assunto')
            data = email.get('receivedDateTime', 'N/A')
            print(f"  [{data[:10]}] {subj[:80]}")

            if '0123456' in subj or '0123456' in email.get('bodyPreview', ''):
                print(f"\n✅ ENCONTRADO COM NUMERO!")
                print(f"Assunto: {subj}")
                print(f"De: {email.get('from', {}).get('emailAddress', {}).get('address')}")
                print(f"Data: {data}")
                print(f"Corpo: {email.get('bodyPreview', '')[:300]}")
                encontrado = True

    if not encontrado:
        print(f"\n❌ Nenhum email de raphaeldcb@gmail.com contem '0123456'")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
