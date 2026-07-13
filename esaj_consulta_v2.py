#!/usr/bin/env python3
"""Automação Consulta ESAJ v2 — mais robusta, descobre elementos dinamicamente."""
import sys
import json
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime


def run_agent_browser(args: list) -> tuple[int, str]:
    """Execute agent-browser command and return (returncode, stdout)."""
    result = subprocess.run(
        ["agent-browser"] + args,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.returncode, result.stdout


def snapshot_i() -> str:
    """Do `agent-browser snapshot -i` and return stdout."""
    code, stdout = run_agent_browser(["snapshot", "-i"])
    return stdout if code == 0 else ""


def find_ref_by_text(snapshot_text: str, needle: str) -> str | None:
    """Extract ref (@eN) for line containing needle."""
    for line in snapshot_text.split("\n"):
        if needle.lower() in line.lower():
            # Extract eN from [ref=eN]
            match = re.search(r"\[ref=e(\d+)\]", line)
            if match:
                return f"@e{match.group(1)}"
    return None


def parse_cnj(numero_cnj: str) -> tuple[str, str]:
    """Split CNJ number into (primeiros_13, ultimos_4)."""
    limpo = numero_cnj.replace("-", "").replace(".", "")
    if len(limpo) < 20:
        raise ValueError(f"CNJ inválido: {numero_cnj}")
    return limpo[:13], limpo[-4:]


def main():
    print("🔍 Automação Consulta ESAJ v2")
    print("=" * 60)

    # Passo 1: Abrir ESAJ
    print("\n[1] Abrindo ESAJ...")
    run_agent_browser(["close", "--all"])  # Limpa sessions anteriores
    time.sleep(1)
    code, _ = run_agent_browser(["open", "https://esaj.tjms.jus.br/cjsg/"])
    if code != 0:
        print("✗ Erro ao abrir ESAJ")
        return 1
    print("✓ ESAJ aberto")
    time.sleep(2)

    # Passo 2: Encontrar menu "Consultas"
    print("\n[2] Encontrando menu Consultas...")
    snap1 = snapshot_i()
    ref_consultas = find_ref_by_text(snap1, "Consultas")
    if not ref_consultas:
        print("✗ Menu Consultas não encontrado")
        return 1
    print(f"✓ Menu encontrado: {ref_consultas}")

    # Passo 2b: Clicar em Consultas para expandir
    print("\n[2b] Clicando em Consultas...")
    run_agent_browser(["click", ref_consultas])
    time.sleep(1)

    # Passo 2c: Encontrar "Consulta de Processos de 1º Grau"
    print("\n[2c] Encontrando Consulta de 1º Grau...")
    snap1b = snapshot_i()
    ref_consulta_1g = find_ref_by_text(snap1b, "Consulta de Processos de 1º Grau")
    if not ref_consulta_1g:
        print("✗ Consulta de 1º Grau não encontrada")
        print("   Snapshot:")
        print(snap1b[:500])
        return 1
    print(f"✓ Link encontrado: {ref_consulta_1g}")

    # Passo 3: Clicar em "Consulta de Processos de 1º Grau"
    print("\n[3] Clicando em Consulta de 1º Grau...")
    code, _ = run_agent_browser(["click", ref_consulta_1g])
    if code != 0:
        print("✗ Erro ao clicar")
        return 1
    print("✓ Clicado")
    time.sleep(2)

    # Passo 4: Descobrir campos de entrada
    print("\n[4] Descobrindo campos de entrada...")
    snap2 = snapshot_i()

    input_primeiros = find_ref_by_text(snap2, "Número do processo")
    input_ultimos = find_ref_by_text(snap2, "últimos")
    botao_consultar = find_ref_by_text(snap2, "Consultar")

    if not (input_primeiros and input_ultimos and botao_consultar):
        print(f"✗ Campos não encontrados:")
        print(f"    primeiros: {input_primeiros}")
        print(f"    últimos: {input_ultimos}")
        print(f"    botão: {botao_consultar}")
        return 1

    print(f"✓ Campos encontrados:")
    print(f"    Primeiros: {input_primeiros}")
    print(f"    Últimos: {input_ultimos}")
    print(f"    Botão: {botao_consultar}")

    # Passo 5: Preencher e consultar
    print("\n[5] Preenchendo formulário...")
    numero_cnj = "0501238-67.0212.8.12.0001"
    primeiros, ultimos = parse_cnj(numero_cnj)

    code, _ = run_agent_browser(["fill", input_primeiros, primeiros])
    if code != 0:
        print(f"✗ Erro ao preencher primeiros: {primeiros}")
        return 1
    print(f"✓ Primeiros preenchidos: {primeiros}")

    code, _ = run_agent_browser(["fill", input_ultimos, ultimos])
    if code != 0:
        print(f"✗ Erro ao preencher últimos: {ultimos}")
        return 1
    print(f"✓ Últimos preenchidos: {ultimos}")

    time.sleep(0.5)

    # Passo 6: Clicar Consultar
    print("\n[6] Clicando Consultar...")
    code, _ = run_agent_browser(["click", botao_consultar])
    if code != 0:
        print("✗ Erro ao clicar botão")
        return 1
    print("✓ Botão clicado")

    time.sleep(3)

    # Passo 7: Capturar resultado
    print("\n[7] Capturando resultado...")
    run_agent_browser(["screenshot"])
    snap3 = snapshot_i()

    # Detectar se houve resultado ou erro
    if "Não existem informações" in snap3:
        resultado_tipo = "sem resultados (processo não encontrado)"
    elif "Erro" in snap3 or "erro" in snap3:
        resultado_tipo = "erro na consulta"
    else:
        resultado_tipo = "consulta executada"

    # Salvar resultado
    output_dir = Path("/tmp/esaj_consultas")
    output_dir.mkdir(exist_ok=True)

    safe_name = re.sub(r'[^\w-]', '_', numero_cnj)
    output = {
        "timestamp": datetime.now().isoformat(),
        "numero_cnj": numero_cnj,
        "resultado": resultado_tipo,
        "partes": {"primeiros": primeiros, "ultimos": ultimos},
        "refs_usados": {
            "input_primeiros": input_primeiros,
            "input_ultimos": input_ultimos,
            "botao_consultar": botao_consultar,
        },
    }

    output_file = output_dir / f"{safe_name}_resultado.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\n✓ Resultado: {resultado_tipo}")
    print(f"📁 Salvo em: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
