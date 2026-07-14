"""
Executor Selenium para baixar autos do PJe TJMT.
Chamado pelo mac_agent.py quando Job tipo='pje_download_autos' chega.
"""

import os
import time
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyotp

CHROME_REMOTE_DEBUG_PORT = 9222
TIMEOUT = 30


def conectar_chrome_remoto(host="127.0.0.1", port=CHROME_REMOTE_DEBUG_PORT):
    opcoes = webdriver.ChromeOptions()
    opcoes.debugger_address = f"{host}:{port}"
    return webdriver.Chrome(options=opcoes)


def _parse_cnj(numero: str) -> dict:
    numero = re.sub(r"\D", "", numero)
    assert len(numero) == 20, f"CNJ inválido: {numero}"
    return {
        "seq": numero[0:7],
        "dv": numero[7:9],
        "ano": numero[9:13],
        "justica": numero[13:14],
        "tribunal": numero[14:16],
        "orgao": numero[16:20],
    }


def obter_2fa_totp() -> str:
    secret = os.getenv("PJE_TOTP_SECRET")
    if not secret:
        raise RuntimeError("PJE_TOTP_SECRET não configurado")
    totp = pyotp.TOTP(secret)
    codigo = totp.now()
    print(f"[2FA] Código TOTP gerado: {codigo}")
    return codigo


def obter_2fa_manual() -> str:
    print("[2FA] Abra seu Google Authenticator e digite o código de 6 dígitos:")
    codigo = input("Código: ").strip()
    if not codigo.isdigit() or len(codigo) != 6:
        raise ValueError("Código inválido. Deve ser 6 dígitos.")
    return codigo


def obter_2fa() -> str:
    try:
        return obter_2fa_totp()
    except RuntimeError:
        print("[2FA] TOTP não configurado, solicitando manualmente...")
        return obter_2fa_manual()


def _buscar_pdf_baixado(numero_cnj: str) -> Path:
    downloads_dir = Path.home() / "Downloads"
    pdfs = sorted(
        downloads_dir.glob("*.pdf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if pdfs:
        return pdfs[0]
    raise FileNotFoundError(f"PDF não encontrado em {downloads_dir}")


def baixar_autos_pje(numero_cnj: str, driver=None) -> Path:
    if not driver:
        driver = conectar_chrome_remoto()

    try:
        partes_cnj = _parse_cnj(numero_cnj)
        driver.get("https://pje.tjmt.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam")

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

        botao_pesquisar = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Pesquisar')]"))
        )
        botao_pesquisar.click()

        link_paginador = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@title='Abrir Paginador']"))
        )

        abas_antes = driver.window_handles
        link_paginador.click()

        try:
            WebDriverWait(driver, 2).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except:
            pass

        WebDriverWait(driver, TIMEOUT).until(lambda d: len(d.window_handles) > len(abas_antes))
        aba_paginador = [h for h in driver.window_handles if h not in abas_antes][0]
        driver.switch_to.window(aba_paginador)

        botao_download_autos = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Download autos do processo')]"))
        )
        botao_download_autos.click()

        botao_download = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Download']"))
        )

        abas_antes2 = driver.window_handles
        botao_download.click()

        WebDriverWait(driver, TIMEOUT).until(lambda d: len(d.window_handles) > len(abas_antes2))
        aba_pdf = [h for h in driver.window_handles if h not in abas_antes2][0]

        time.sleep(2)

        driver.switch_to.window(aba_pdf)
        driver.close()
        driver.switch_to.window(aba_paginador)
        driver.close()
        driver.switch_to.window(abas_antes[0])

        pdf_path = _buscar_pdf_baixado(numero_cnj)
        return pdf_path

    except Exception as e:
        raise RuntimeError(f"Erro ao baixar autos {numero_cnj}: {e}")


def enviar_para_armazenamento(caminho_pdf_local: Path, numero_cnj: str) -> str:
    dest_dir = Path("/home/perito/dados/pdfs/pje_tjmt")
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / f"{numero_cnj.replace('.', '_').replace('-', '_')}.pdf"

    import shutil
    shutil.copy2(caminho_pdf_local, dest_path)

    return str(dest_path)


def executar_job(payload: dict) -> dict:
    numero_cnj = payload["numero_cnj"]
    tribunal = payload.get("tribunal", "TJMT")

    print(f"[PJe] Iniciando download {numero_cnj}...")

    driver = conectar_chrome_remoto()

    try:
        pdf_local = baixar_autos_pje(numero_cnj, driver)
        print(f"[PJe] PDF baixado: {pdf_local}")

        pdf_final = enviar_para_armazenamento(pdf_local, numero_cnj)
        print(f"[PJe] Armazenado: {pdf_final}")

        return {
            "sucesso": True,
            "numero_cnj": numero_cnj,
            "pdf_path": str(pdf_final),
            "tamanho_bytes": pdf_local.stat().st_size
        }

    except Exception as e:
        print(f"[PJe] Erro: {e}")
        return {
            "sucesso": False,
            "numero_cnj": numero_cnj,
            "erro": str(e)
        }


if __name__ == "__main__":
    payload = {"numero_cnj": "1234567-89.2020.8.28.0001", "tribunal": "TJMT"}
    resultado = executar_job(payload)
    print(resultado)
