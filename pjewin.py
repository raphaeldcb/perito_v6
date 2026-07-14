#!/usr/bin/env python3
"""
Executor Selenium para baixar autos do PJe TJMT — Windows (com A3)
Chamado pelo agent Windows quando Job tipo='pje_download_autos' chega.

Assume que:
- Chrome está aberto no Windows com A3 já autenticado (8h de token)
- Chave ed25519 para SSH ao VPS está configurada
- OneDrive está sincronizado localmente
"""

import os
import re
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import shutil

TIMEOUT = 30


def parse_cnj(numero: str) -> dict:
    """Parse CNJ em 7+2+4+1+2+4 dígitos."""
    numero = re.sub(r"\D", "", numero)
    if len(numero) != 20:
        raise ValueError(f"CNJ inválido: {numero}")
    return {
        "seq": numero[0:7],
        "dv": numero[7:9],
        "ano": numero[9:13],
        "justica": numero[13:14],
        "tribunal": numero[14:16],
        "orgao": numero[16:20],
    }


def conectar_chrome_windows(chrome_path: str = None) -> webdriver.Chrome:
    """
    Conecta ao Chrome aberto no Windows.

    Opções:
    1. Chrome com --remote-debugging-port=9222 (debugger_address)
    2. ChromeDriver local (fallback)
    """
    try:
        # Tenta via remote debugging (Chrome já aberto)
        options = webdriver.ChromeOptions()
        options.debugger_address = "127.0.0.1:9222"
        driver = webdriver.Chrome(options=options)
        print("[A3] Conectado via remote debugging (Chrome já aberto)")
        return driver
    except:
        # Fallback: usar ChromeDriver local
        if chrome_path is None:
            chrome_path = "chromedriver.exe"  # Assume no PATH
        service = Service(chrome_path)
        driver = webdriver.Chrome(service=service)
        print("[A3] Conectado via ChromeDriver local")
        return driver


def buscar_pdf_windows(numero_cnj: str) -> Path:
    """
    Busca PDF na pasta Downloads do Windows.
    Chrome baixa automaticamente lá.
    """
    downloads = Path.home() / "Downloads"
    pdfs = sorted(
        downloads.glob("*.pdf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if pdfs:
        return pdfs[0]
    raise FileNotFoundError(f"PDF não encontrado em {downloads}")


def baixar_autos_pje(numero_cnj: str, driver=None) -> Path:
    """
    Fluxo completo no PJe TJMT:
    1. Navega para https://pje.tjmt.jus.br
    2. Preenche número CNJ em 6 campos
    3. Clica Pesquisar
    4. Abre paginador (nova aba)
    5. Clica "Download autos do processo"
    6. Clica "Download"
    7. Retorna path do PDF baixado

    Assume A3 já autenticado (8h de token).
    """
    if driver is None:
        driver = conectar_chrome_windows()

    try:
        partes_cnj = parse_cnj(numero_cnj)

        # Navega para PJe
        driver.get("https://pje.tjmt.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam")
        print(f"[PJe] Navegando para {numero_cnj}")

        # Preenche 6 campos do CNJ
        campos = [
            ("//label[contains(.,'Número do processo')]/following::input[1]", partes_cnj["seq"]),
            ("//label[contains(.,'Número do processo')]/following::input[2]", partes_cnj["dv"]),
            ("//label[contains(.,'Número do processo')]/following::input[3]", partes_cnj["ano"]),
            ("//label[contains(.,'Número do processo')]/following::input[4]", partes_cnj["justica"]),
            ("//label[contains(.,'Número do processo')]/following::input[5]", partes_cnj["tribunal"]),
            ("//label[contains(.,'Número do processo')]/following::input[6]", partes_cnj["orgao"]),
        ]

        for xpath, valor in campos:
            elem = WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            elem.clear()
            elem.send_keys(valor)
            print(f"  ✓ Preencheu {valor}")

        # Clica Pesquisar
        botao_pesquisar = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Pesquisar')]"))
        )
        botao_pesquisar.click()
        print("  ✓ Pesquisou")

        # Abre paginador
        link_paginador = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@title='Abrir Paginador']"))
        )

        abas_antes = driver.window_handles
        link_paginador.click()

        # Descarta alerta se houver
        try:
            WebDriverWait(driver, 2).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except:
            pass

        # Muda para aba paginador
        WebDriverWait(driver, TIMEOUT).until(lambda d: len(d.window_handles) > len(abas_antes))
        aba_paginador = [h for h in driver.window_handles if h not in abas_antes][0]
        driver.switch_to.window(aba_paginador)
        print("  ✓ Abriu paginador")

        # Download autos do processo
        botao_download_autos = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Download autos do processo')]"))
        )
        botao_download_autos.click()
        print("  ✓ Clicou 'Download autos'")

        # Download (final)
        botao_download = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Download']"))
        )

        abas_antes2 = driver.window_handles
        botao_download.click()
        print("  ✓ Clicou 'Download'")

        # Aba PDF abre, fecha automaticamente
        WebDriverWait(driver, TIMEOUT).until(lambda d: len(d.window_handles) > len(abas_antes2))
        aba_pdf = [h for h in driver.window_handles if h not in abas_antes2][0]

        time.sleep(2)  # Tempo para PDF começar download

        driver.switch_to.window(aba_pdf)
        driver.close()
        driver.switch_to.window(aba_paginador)
        driver.close()
        driver.switch_to.window(abas_antes[0])  # Volta à principal

        # Busca PDF em Downloads
        pdf_path = buscar_pdf_windows(numero_cnj)
        print(f"  ✓ PDF baixado: {pdf_path}")
        return pdf_path

    except Exception as e:
        raise RuntimeError(f"Erro ao baixar autos {numero_cnj}: {e}")


def enviar_para_onedrive(caminho_pdf_local: Path, numero_cnj: str) -> str:
    """
    Copia PDF para pasta OneDrive sincronizada no Windows.

    Caminho padrão:
    C:\\Users\\{user}\\OneDrive - Bibliotecas Compartilhadas\\IPCMS - ARQUIVOS\\PROCESSOS\\intimações baixadas
    """
    # Configurável via env var, com fallback
    onedrive_base = os.getenv("ONEDRIVE_INTIMACOES_PATH")

    if not onedrive_base:
        # Tenta descobrir automaticamente
        onedrive_base = Path.home() / "OneDrive - Bibliotecas Compartilhadas" / "IPCMS - ARQUIVOS" / "PROCESSOS" / "intimações baixadas"

    onedrive_base = Path(onedrive_base)

    if not onedrive_base.exists():
        raise FileNotFoundError(f"Pasta OneDrive não encontrada: {onedrive_base}")

    # Nome do arquivo: CNJ com underscores
    nome_arquivo = f"{numero_cnj.replace('.', '_').replace('-', '_')}.pdf"
    dest_path = onedrive_base / nome_arquivo

    # Copia
    shutil.copy2(caminho_pdf_local, dest_path)
    print(f"  ✓ Salvo em OneDrive: {dest_path}")

    return str(dest_path)


def executar_job(payload: dict) -> dict:
    """
    Executa job de download de autos.
    Chamado pelo agent Windows quando recebe Job tipo='pje_download_autos'.

    Retorna:
    {
        "sucesso": True/False,
        "numero_cnj": "...",
        "pdf_path": "...",  # se sucesso
        "tamanho_bytes": ...,
        "erro": "..."  # se falha
    }
    """
    numero_cnj = payload["numero_cnj"]
    tribunal = payload.get("tribunal", "TJMT")

    print(f"\n[PJe] Iniciando download: {numero_cnj}")

    driver = None
    try:
        driver = conectar_chrome_windows()

        # Baixa do PJe
        pdf_local = baixar_autos_pje(numero_cnj, driver)

        # Envia para OneDrive
        pdf_final = enviar_para_onedrive(pdf_local, numero_cnj)

        tamanho = pdf_local.stat().st_size
        print(f"[PJe] ✅ Sucesso: {tamanho} bytes")

        return {
            "sucesso": True,
            "numero_cnj": numero_cnj,
            "pdf_path": str(pdf_final),
            "tamanho_bytes": tamanho
        }

    except Exception as e:
        print(f"[PJe] ❌ Erro: {e}")
        return {
            "sucesso": False,
            "numero_cnj": numero_cnj,
            "erro": str(e)
        }

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    # Teste local
    import json

    payload = {
        "numero_cnj": "0000038-16.2016.8.11.0019",
        "tribunal": "TJMT"
    }

    resultado = executar_job(payload)
    print(json.dumps(resultado, indent=2))
