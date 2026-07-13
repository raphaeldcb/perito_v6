#!/usr/bin/env python3
"""
Filtro de intimações — extrai processos de emails recebidos em adm@ipcms.com.br

Fluxo:
1. Conecta ao Office 365 (Graph API via VPS)
2. Busca emails em adm@ipcms.com.br com palavras-chave ("intimação", "citação", etc)
3. Extrai números de processo (CNJ) dos emails
4. Enfileira consultas ESAJ via API do Perito v6
5. Persiste intimações vinculadas aos processos encontrados

Nota: integra com rota POST /api/v1/consultas-esaj/enfileirar
"""
import sys
import json
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path

# API endpoint do Perito v6
API_BASE = "http://localhost:5000"  # ou https://sistema.ipcms.com.br quando em produção

# Regex para CNJ (formato: NNNNNNN-DD.AAAA.J.TT.OOOO)
CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")

# Email a monitorar
EMAIL_TARGET = "adm@ipcms.com.br"


def extrair_cnj_de_texto(texto: str) -> list[str]:
    """Extrai todos os números CNJ de um texto."""
    matches = CNJ_RE.findall(texto)
    return list(set(matches))  # Remove duplicatas


def buscar_emails_intimacoes() -> list[dict]:
    """Busca emails de intimação via API do Perito (que conecta ao Graph)."""
    # TODO: implementar via rota /api/v1/emails?folder=inbox&keywords=intimação
    # Por enquanto, retorna lista vazia
    print("[!] TODO: implementar busca de emails via Graph API")
    return []


def enfileirar_consulta(numero_cnj: str, origem: str = "email") -> bool:
    """Enfileira uma consulta ESAJ via API do Perito v6."""
    try:
        resposta = requests.post(
            f"{API_BASE}/api/v1/consultas-esaj/enfileirar",
            json={
                "numero_cnj": numero_cnj,
                "origem": origem,
                "timestamp": datetime.now().isoformat(),
            },
            timeout=10,
        )
        if resposta.status_code in (200, 201):
            print(f"  ✓ Consulta {numero_cnj} enfileirada")
            return True
        else:
            print(f"  ✗ Erro ao enfileirar {numero_cnj}: {resposta.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Erro de conexão ao enfileirar {numero_cnj}: {e}")
        return False


def main():
    """Fluxo principal: busca emails, extrai CNJ, enfileira consultas."""
    print("📧 Filtro de Intimações — Email adm@ipcms.com.br")
    print("=" * 60)

    # Passo 1: Buscar emails
    print(f"\n[1] Buscando emails em {EMAIL_TARGET}...")
    emails = buscar_emails_intimacoes()
    if not emails:
        print("   (Nenhum email encontrado ou API não implementada ainda)")
        print("   → Próximo passo: implementar rota de busca de emails")
        return 0

    # Passo 2: Processar cada email
    processados = 0
    cnj_encontrados = set()

    print(f"\n[2] Processando {len(emails)} emails...")
    for email in emails:
        assunto = email.get("subject", "")
        corpo = email.get("body", "")
        data_recebido = email.get("receivedDateTime", "")

        print(f"\n   📄 {assunto[:60]}...")
        print(f"      Recebido: {data_recebido}")

        # Extrair CNJ
        cnj_lista = extrair_cnj_de_texto(f"{assunto} {corpo}")
        if cnj_lista:
            print(f"      Encontrados: {cnj_lista}")
            cnj_encontrados.update(cnj_lista)
        else:
            print(f"      Nenhum CNJ encontrado")

        processados += 1

    # Passo 3: Enfileirar consultas ESAJ
    print(f"\n[3] Enfileirando {len(cnj_encontrados)} processos...")
    enfileirados = 0
    for cnj in sorted(cnj_encontrados):
        if enfileirar_consulta(cnj, origem="email_adm"):
            enfileirados += 1

    # Resumo
    print(f"\n{'=' * 60}")
    print(f"✓ Processados: {processados} emails")
    print(f"✓ CNJ encontrados: {len(cnj_encontrados)}")
    print(f"✓ Enfileirados: {enfileirados} consultas")

    # Salvar resultado
    output_dir = Path("/tmp/filtro_intimacoes")
    output_dir.mkdir(exist_ok=True)

    resultado = {
        "timestamp": datetime.now().isoformat(),
        "emails_processados": processados,
        "cnj_encontrados": sorted(cnj_encontrados),
        "consultas_enfileiradas": enfileirados,
    }

    output_file = output_dir / f"resultado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(resultado, indent=2, ensure_ascii=False))
    print(f"\n📁 Resultado salvo em: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
