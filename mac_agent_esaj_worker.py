#!/usr/bin/env python3
"""Mac agent: monitora fila /api/v1/consultas-esaj/fila e executa automação."""
import sys
import time
import requests
import subprocess
import json
from pathlib import Path

API_BASE = "http://localhost:5000"
POLL_INTERVAL = 30  # segundos


def obter_fila() -> list:
    """GET /fila — retorna lista de jobs na_fila."""
    try:
        r = requests.get(f"{API_BASE}/api/v1/consultas-esaj/fila?limit=10", timeout=5)
        if r.status_code == 200:
            return r.json().get("items", [])
    except:
        pass
    return []


def executar_consulta(numero_cnj: str) -> dict:
    """Roda esaj_consulta_v2.py e retorna resultado."""
    try:
        result = subprocess.run(
            ["python3", "/Users/ipc_server/esaj_consulta_v2.py"],
            capture_output=True,
            text=True,
            timeout=120,
            env={"CNJ_PADRAO": numero_cnj}
        )
        resultado = {
            "numero_cnj": numero_cnj,
            "resultado": "sucesso" if result.returncode == 0 else "erro",
            "stdout": result.stdout[-500:] if result.stdout else "",
        }
        return resultado
    except Exception as e:
        return {
            "numero_cnj": numero_cnj,
            "resultado": "erro",
            "error": str(e),
        }


def reportar_resultado(job_id: int, numero_cnj: str, resultado: str):
    """POST / — registra resultado da consulta."""
    try:
        r = requests.post(
            f"{API_BASE}/api/v1/consultas-esaj/",
            json={
                "numero_cnj": numero_cnj,
                "resultado": resultado,
                "partes": {"primeiros": numero_cnj[:13], "ultimos": numero_cnj[-4:]},
                "refs_usados": {},
            },
            timeout=5,
        )
        return r.status_code in (200, 201)
    except:
        return False


def main():
    print("🤖 Mac Agent — ESAJ Consulta Worker")
    print("=" * 60)

    while True:
        fila = obter_fila()
        if fila:
            print(f"\n[{time.strftime('%H:%M:%S')}] Fila: {len(fila)} job(s)")
            for job in fila:
                numero_cnj = job.get("numero_cnj")
                job_id = job.get("id")

                print(f"  ⚙️ Job {job_id}: {numero_cnj}")
                resultado = executar_consulta(numero_cnj)
                reportar_resultado(job_id, numero_cnj, resultado["resultado"])
                print(f"     ✓ Reportado: {resultado['resultado']}")

        else:
            print(f"[{time.strftime('%H:%M:%S')}] Nenhum job na fila, aguardando...")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Worker finalizado")
        sys.exit(0)
