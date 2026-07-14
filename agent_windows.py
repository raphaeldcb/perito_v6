#!/usr/bin/env python3
"""
Agent Windows: polling de jobs PJe + protocolo via A3.

Roda no Windows (Bruno) — detecta jobs na fila do VPS e executa.

Uso:
  set PERITO_API_URL=http://129.121.34.186:8000
  set AGENT_API_KEY=perito-mac-agent-key-v6-2026-07-14
  python agent_windows.py

ou via PowerShell:
  $env:PERITO_API_URL = "http://129.121.34.186:8000"
  $env:AGENT_API_KEY = "perito-mac-agent-key-v6-2026-07-14"
  python agent_windows.py
"""

import logging
import os
import sys
import time
import requests
from pathlib import Path

# ============ CONFIG ============
API_URL = os.environ.get("PERITO_API_URL", "http://129.121.34.186:8000").rstrip("/")
AGENT_KEY = os.environ.get("AGENT_API_KEY", "perito-mac-agent-key-v6-2026-07-14")
POLL_SEGUNDOS = int(os.environ.get("AGENT_POLL_SEGUNDOS", "30"))

HEADERS = {"X-Agent-Key": AGENT_KEY}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("windows-agent")

# ============ IMPORTAR EXECUTORES ============
try:
    from pjewin import executar_job as executar_pje
    logger.info("✅ pjewin importado")
except ImportError as e:
    logger.warning(f"⚠️  pjewin não encontrado: {e}")
    executar_pje = None

try:
    # Seu executor existente de protocolo
    # from seu_protocolo import executar_protocolo
    # para agora é None
    executar_protocolo = None
except ImportError:
    logger.warning("⚠️  protocolo executor não configurado")
    executar_protocolo = None


# ============ ROTEIROS DE JOBS ============

EXECUTORES = {
    "pje_download_autos": executar_pje,
    # "protocolo": executar_protocolo,
    # ... adicione outros conforme necessário
}


# ============ FUNÇÕES ============

def obter_proximo_job(tipo_filtro: str = None) -> dict:
    """GET /api/v1/pje/fila — lista jobs pendentes (PJe)."""
    try:
        params = {"limit": 5, "status_filtro": "na_fila"}
        if tipo_filtro:
            params["tipo"] = tipo_filtro

        resp = requests.get(
            f"{API_URL}/api/v1/pje/fila",
            headers=HEADERS,
            params=params,
            timeout=15
        )
        resp.raise_for_status()

        data = resp.json()
        items = data.get("items", [])
        return items[0] if items else None

    except Exception as e:
        logger.warning(f"Erro ao buscar fila: {e}")
        return None


def processar_job(job: dict) -> bool:
    """Executa um job."""
    job_id = job.get("id")
    job_tipo = job.get("payload", {}).get("tipo") or "pje_download_autos"

    logger.info(f"▶️  Job {job_id} ({job_tipo}): {job.get('payload', {})}")

    executor = EXECUTORES.get(job_tipo)
    if not executor:
        logger.error(f"❌ Tipo desconhecido: {job_tipo}")
        relatar_erro(job_id, f"Tipo de job desconhecido: {job_tipo}")
        return False

    try:
        payload = dict(job.get("payload") or {})
        resultado = executor(payload)

        logger.info(f"✅ Job {job_id} concluído")
        relatar_sucesso(job_id, resultado)
        return True

    except Exception as e:
        logger.error(f"❌ Job {job_id} falhou: {e}")
        relatar_erro(job_id, str(e)[:2000])
        return False


def relatar_sucesso(job_id: int, resultado: dict) -> bool:
    """PATCH /api/v1/pje/{job_id}/concluir — reporta sucesso."""
    try:
        corpo = {"sucesso": True, "resultado": resultado}
        resp = requests.patch(
            f"{API_URL}/api/v1/pje/{job_id}/concluir",
            headers=HEADERS,
            json=corpo,
            timeout=30
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Erro ao reportar sucesso job {job_id}: {e}")
        return False


def relatar_erro(job_id: int, erro: str) -> bool:
    """PATCH /api/v1/pje/{job_id}/concluir — reporta erro."""
    try:
        corpo = {"sucesso": False, "erro": erro}
        resp = requests.patch(
            f"{API_URL}/api/v1/pje/{job_id}/concluir",
            headers=HEADERS,
            json=corpo,
            timeout=30
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Erro ao reportar erro job {job_id}: {e}")
        return False


def loop_principal():
    """Loop infinito: poll → processa → aguarda."""
    logger.info("=" * 60)
    logger.info(f"🤖 Agent Windows iniciado")
    logger.info(f"🔗 API: {API_URL}")
    logger.info(f"⏱️  Poll: {POLL_SEGUNDOS}s")
    logger.info("=" * 60)

    tentativas_sem_job = 0

    while True:
        try:
            job = obter_proximo_job()

            if job:
                tentativas_sem_job = 0
                processar_job(job)
            else:
                tentativas_sem_job += 1
                if tentativas_sem_job == 1:
                    logger.info(f"💤 Nenhum job na fila, aguardando...")
                elif tentativas_sem_job % 10 == 0:
                    logger.info(f"   Ainda aguardando ({tentativas_sem_job * POLL_SEGUNDOS}s)...")

            time.sleep(POLL_SEGUNDOS)

        except KeyboardInterrupt:
            logger.info("\n👋 Agent finalizado (CTRL+C)")
            break
        except Exception as e:
            logger.error(f"Erro não tratado: {e}")
            time.sleep(POLL_SEGUNDOS)


# ============ MAIN ============

if __name__ == "__main__":
    if not executar_pje:
        logger.error("❌ pjewin não disponível — coloque pjewin.py no mesmo diretório")
        sys.exit(1)

    try:
        loop_principal()
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
