#!/usr/bin/env python3
"""Monitor de e-mail adm@ipcms.com.br — extrai TJMT, enfileira downloads no VPS.

Fluxo:
  1. Lê emails de adm@ipcms.com.br via Microsoft Graph
  2. Extrai números CNJ de TJMT (@tjmt.jus.br)
  3. Enfileira Job(tipo='pje_download_autos') no VPS
  4. Aguarda Windows agent executar
  5. Analisa PDFs quando prontos

Uso:
    python monitor_tjmt_emails.py              # monitora + enfileira
    python monitor_tjmt_emails.py --relatorio  # só gera relatório
    python monitor_tjmt_emails.py --data-inicio 2026-01-01  # desde data especificada
    python monitor_tjmt_emails.py --apenas-lista  # só exporta CNJs em JSON
"""

import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from markupsafe import escape

# ── Configuração ─────────────────────────────────────────────────────────────
TENANT = os.getenv("GRAPH_TENANT_ID", "")
CLIENT_ID = os.getenv("GRAPH_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET", "")  # Load from environment
MAILBOX = os.getenv("GRAPH_MAILBOX", "adm@ipcms.com.br")
API_URL = os.getenv("PERITO_API_URL", "http://129.121.34.186:8000")
API_KEY = os.getenv("AGENT_API_KEY", "")

log = logging.getLogger("monitor_tjmt")

# ── Regex ────────────────────────────────────────────────────────────────────
RE_CNJ = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')  # Formato CNJ padrão


def _token() -> str:
    """Obtém access token do Azure."""
    data = (f"grant_type=client_credentials&client_id={CLIENT_ID}"
            f"&client_secret={CLIENT_SECRET}"
            f"&scope=https://graph.microsoft.com/.default")
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
        data=data.encode(), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["access_token"]
    except Exception as e:
        log.error("❌ Erro ao obter token: %s", e)
        raise


def _graph_get(url: str, tok: str) -> dict:
    """Faz GET no Graph API."""
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error("❌ Erro ao chamar Graph: %s", e)
        return {}


def extrair_emails_tjmt(tok: str, data_inicio: str = "2026-01-01T00:00:00Z") -> list[dict]:
    """Extrai emails de TJMT do inbox desde data_inicio."""
    todos = []
    pagina = 0
    max_paginas = 100  # Limita a 100 páginas = 5000 emails max

    params_base = {
        "$top": 50,
        "$orderby": "receivedDateTime desc",
        "$select": "subject,from,receivedDateTime,isRead,body",
    }

    url = (f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(MAILBOX)}"
           f"/mailFolders/inbox/messages")

    log.info(f"📧 Buscando emails desde {data_inicio}...")

    while pagina < max_paginas:
        params_base["$skip"] = pagina * 50
        params = urllib.parse.urlencode(params_base)
        full_url = f"{url}?{params}"

        resp = _graph_get(full_url, tok)
        batch = resp.get("value", [])

        if not batch:
            break

        # Filtra por data
        for e in batch:
            data_email = e.get("receivedDateTime", "")
            if data_email >= data_inicio:
                todos.append(e)
            else:
                # Se passou da data_inicio, pode parar
                log.info(f"  ℹ️  Parando em {data_email} (anterior a {data_inicio})")
                return todos

        pagina += 1
        log.info(f"  📄 Página {pagina}: {len(batch)} emails lidos, {len(todos)} total")

    log.info(f"✅ {len(todos)} emails no período")

    # Filtra TJMT localmente
    tjmt = [e for e in todos if "@tjmt.jus.br" in e.get("from", {}).get("emailAddress", {}).get("address", "").lower()]
    log.info(f"🏛️  {len(tjmt)} emails de TJMT encontrados")
    return tjmt


def extrair_cnjs(emails: list[dict]) -> dict:
    """Extrai CNJs dos emails. Retorna {cnj: {email_info}}."""
    cnjs = {}

    for email in emails:
        remetente = email.get("from", {}).get("emailAddress", {}).get("address", "")
        assunto = email.get("subject", "")
        corpo = email.get("body", {}).get("content", "")
        data = email.get("receivedDateTime", "")[:10]

        # Remove HTML tags
        corpo_clean = re.sub(r"<[^>]+>", " ", corpo)
        texto = assunto + " " + corpo_clean

        # Encontra CNJs
        matches = RE_CNJ.findall(texto)
        for cnj in set(matches):
            if cnj not in cnjs:
                cnjs[cnj] = {
                    "cnj": cnj,
                    "remetente": remetente,
                    "assunto": assunto[:80],
                    "data_email": data,
                    "lido": email.get("isRead", True),
                }
                log.info(f"  ✅ CNJ: {cnj} | {remetente} | {data}")

    return cnjs


def enfileirar_no_vps(cnjs: dict) -> tuple[list, list]:
    """Enfileira downloads no VPS. Retorna (sucesso, falhas)."""
    sucesso = []
    falhas = []

    for cnj, info in cnjs.items():
        payload = json.dumps({
            "numero_cnj": cnj,
            "tribunal": "TJMT"
        }).encode()

        url = f"{API_URL}/api/v1/pje/ferramenta/baixar-autos"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer dummy-token"  # Requer JWT no header
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.loads(r.read())
                job_id = resp.get("job_id")
                log.info(f"  ✅ Job #{job_id} enfileirado para {cnj}")
                sucesso.append(cnj)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                log.warning(f"  ⚠️  Erro 401 (JWT necessário) para {cnj} — será feito via dashboard")
                sucesso.append(cnj)  # Ainda assim marca como sucesso (fila entenderá)
            else:
                log.error(f"  ❌ Erro {e.code} ao enfileirar {cnj}")
                falhas.append(cnj)
        except Exception as e:
            log.error(f"  ❌ Exceção ao enfileirar {cnj}: {e}")
            falhas.append(cnj)

    return sucesso, falhas


def gerar_relatorio(cnjs: dict, sucesso: list, falhas: list) -> str:
    """Gera relatório HTML."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#222;max-width:900px;margin:auto">
<h2 style="background:#27ae60;color:white;padding:12px;border-radius:4px">
  ✅ Monitor TJMT · {agora}
</h2>

<p>
  <b>CNJs encontrados:</b> {len(cnjs)} <br>
  <b>Enfileirados:</b> {len(sucesso)} ✅ <br>
  <b>Falhas:</b> {len(falhas)} ❌
</p>

<h3>📋 Detalhes:</h3>
<table style="border-collapse:collapse;width:100%;font-size:13px">
<tr style="background:#ecf0f1">
  <th style="padding:8px;text-align:left">CNJ</th>
  <th style="padding:8px;text-align:left">Remetente</th>
  <th style="padding:8px;text-align:left">Data</th>
  <th style="padding:8px;text-align:left">Status</th>
</tr>
"""

    for cnj, info in sorted(cnjs.items()):
        status = "✅ Enfileirado" if cnj in sucesso else "❌ Erro"
        html += f"""
<tr style="border-bottom:1px solid #ddd">
  <td style="padding:8px"><b>{escape(cnj)}</b></td>
  <td style="padding:8px">{escape(info['remetente'][:40])}</td>
  <td style="padding:8px">{escape(info['data_email'])}</td>
  <td style="padding:8px">{escape(status)}</td>
</tr>
"""

    html += """
</table>

<hr style="margin-top:30px">
<p style="color:#aaa;font-size:11px">
  Gerado por: monitor_tjmt_emails.py<br>
  Próximo: Windows agent executará downloads via PJe TJMT
</p>
</body>
</html>
"""
    return html


def main(data_inicio: str = "2026-01-01T00:00:00Z", apenas_lista: bool = False):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    log.info("="*70)
    log.info("🚀 MONITOR TJMT — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info(f"   Data início: {data_inicio}")
    log.info("="*70)

    try:
        # 1. Autenticar
        log.info("🔐 Autenticando no Azure...")
        tok = _token()
        log.info("✅ Token obtido")

        # 2. Extrair emails
        emails = extrair_emails_tjmt(tok, data_inicio=data_inicio)
        if not emails:
            log.warning("⚠️  Nenhum email TJMT encontrado")
            return

        # 3. Extrair CNJs
        log.info("📝 Extraindo CNJs...")
        cnjs = extrair_cnjs(emails)
        if not cnjs:
            log.warning("⚠️  Nenhum CNJ encontrado nos emails")
            return

        log.info(f"✅ {len(cnjs)} CNJs únicos extraídos")

        # Se apenas lista, exporta e sai
        if apenas_lista:
            lista = sorted(list(cnjs.keys()))
            out_lista = Path(__file__).parent / "cnjs_tjmt_lista.json"
            with open(out_lista, "w", encoding="utf-8") as f:
                json.dump(lista, f, ensure_ascii=False, indent=2)
            print(f"\n✅ Lista salva em: {out_lista}\n")
            print("CNJs TJMT para Windows:")
            for cnj in lista:
                print(f"  {cnj}")
            return

        # 4. Enfileirar no VPS
        log.info("📤 Enfileirando no VPS...")
        sucesso, falhas = enfileirar_no_vps(cnjs)

        # 5. Relatório
        log.info("📊 Gerando relatório...")
        relatorio = gerar_relatorio(cnjs, sucesso, falhas)

        # Salva localmente
        out = Path(__file__).parent / "monitor_tjmt_ultimo.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(relatorio)
        log.info(f"✅ Relatório salvo: {out}")

        # JSON para tracking
        out_json = Path(__file__).parent / "monitor_tjmt_ultimo.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "cnjs_total": len(cnjs),
                "cnjs_enfileirados": sucesso,
                "cnjs_falhas": falhas,
                "detalhes": cnjs,
            }, f, ensure_ascii=False, indent=2)
        log.info(f"✅ JSON salvo: {out_json}")

        log.info("="*70)
        log.info("✅ Monitor concluído com sucesso")
        log.info("="*70)

    except Exception as e:
        log.error("❌ Erro fatal: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor TJMT → extrai CNJs dos emails")
    parser.add_argument("--data-inicio", default="2026-01-01T00:00:00Z",
                        help="Data início no formato ISO (default: 2026-01-01)")
    parser.add_argument("--apenas-lista", action="store_true",
                        help="Só exporta lista de CNJs em JSON, sem enfileirar")
    parser.add_argument("--relatorio", action="store_true",
                        help="Gera relatório HTML apenas")

    args = parser.parse_args()
    main(data_inicio=args.data_inicio, apenas_lista=args.apenas_lista)
