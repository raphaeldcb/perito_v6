#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

from app.services import graph_mail

try:
    print("Buscando emails de raphaeldcb@gmail.com em financeiro...")

    # Busca todos os emails (lidos e nao-lidos) - listar_nao_lidos lista os ultimos
    # Vou fazer uma query direta no Graph com filtro

    token = graph_mail._token()
    headers = {"Authorization": f"Bearer {token}"}

    # Filtro para emails de raphaeldcb@gmail.com
    params = {
        "filter": "from/emailAddress/address eq 'raphaeldcb@gmail.com'",
        "top": 50,
        "orderby": "receivedDateTime desc"
    }

    resp = graph_mail._get("/me/mailFolders/inbox/messages", params)
    emails = resp.get("value", [])

    print(f"Total de emails de raphaeldcb@gmail.com: {len(emails)}")

    encontrado = False
    if emails:
        print("\nTodos os emails deste remetente:")
        for email in emails:
            subj = email.get('subject', 'Sem assunto')
            data = email.get('receivedDateTime', 'N/A')
            print(f"  [{data}] {subj[:80]}")

            if '0123456' in subj:
                print(f"\n✅ ENCONTRADO COM NUMERO!")
                encontrado = True

                # Agora pega o corpo completo
                msg_id = email.get('id')
                msg_full = graph_mail._get(f"/me/messages/{msg_id}")
                print(f"Assunto: {msg_full.get('subject')}")
                print(f"De: {msg_full.get('from', {}).get('emailAddress', {}).get('address')}")
                print(f"Data: {msg_full.get('receivedDateTime')}")
                print(f"Corpo preview: {msg_full.get('bodyPreview', '')[:200]}")

    if not encontrado and emails:
        print("\n❌ Nenhum email de raphaeldcb@gmail.com contem '0123456'")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
