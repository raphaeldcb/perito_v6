"""Agente que busca intimações completas: email + ESAJ TJMS/TJMT + Projuris.

Roda no Mac ou Windows como daemon, faz polling de jobs tipo 'esaj_intimacoes'
e executa a busca braçal completa (sem esperar 8 horas).
"""
import logging
import json
import re
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("esaj_intimacoes")

# Credenciais
ESAJ_CPF = os.environ.get("ESAJ_CPF", "00022358110")
ESAJ_SENHA = os.environ.get("ESAJ_SENHA", "Bruno@841124")
EMAIL_USER = os.environ.get("EMAIL_USER", "ipcms@ipcms.com.br")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA", "Bru@8411")

TJS = {
    "TJMS": "https://esaj.tjms.jus.br/cpopg5/open.do",
    "TJMT": "https://esaj.tjmt.jus.br/cpopg5/open.do"
}


def ler_emails_intimacoes():
    """Lê intimações do email e extrai números de processos.
    Retorna: list[{"numero": "...", "data_intimacao": "...", "tj": "..."}]
    """
    try:
        import imaplib
        logger.info("Conectando ao email...")
        imap = imaplib.IMAP4_SSL("outlook.office365.com")
        imap.login(EMAIL_USER, EMAIL_SENHA)
        imap.select("INBOX")

        _, data = imap.search(None, "ALL")
        emails = data[0].split()

        processos = {}  # numero -> {data_intimacao, fonte_tj}

        for email_id in emails[-100:]:  # Últimos 100 emails
            try:
                _, msg = imap.fetch(email_id, "(RFC822)")
                email_body = msg[0][1].decode("utf-8", errors="ignore")

                # Padrão de processo (NNNNNNN-DD.AAAA.J.TT.OOOO)
                matches = re.findall(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", email_body)

                # Tenta extrair data da intimação (aceita múltiplos formatos)
                data_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", email_body)
                data_intimacao = None
                if data_match:
                    try:
                        data_intimacao = f"{data_match.group(3)}-{data_match.group(2).zfill(2)}-{data_match.group(1).zfill(2)}"
                    except:
                        pass

                # Detecta TJ mencionado (TJMS ou TJMT)
                tj_detectado = "TJMS"  # padrão
                if "TJMT" in email_body or "MT" in email_body:
                    tj_detectado = "TJMT"

                for num in matches:
                    if num not in processos:
                        processos[num] = {
                            "numero": num,
                            "data_intimacao": data_intimacao,
                            "tj": tj_detectado
                        }
            except Exception as e:
                logger.warning(f"Erro processando email: {e}")
                continue

        imap.close()
        logger.info(f"✅ Encontrados {len(processos)} processos únicos")
        return list(processos.values())

    except Exception as e:
        logger.error(f"❌ Erro ao ler email: {e}")
        return []


def buscar_processo_esaj(driver, numero, tj_nome):
    """Busca processo no TJ via Selenium e extrai info do ofício.

    Retorna: {
        "numero": "...",
        "tj": "TJMS" | "TJMT",
        "status": "encontrado" | "nao_encontrado" | "erro",
        "data_oficio": "YYYY-MM-DD" ou None,
        "link_autos": "..." ou None,
        "erro": "..." (se status == "erro")
    }
    """
    try:
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        logger.info(f"  🔍 Buscando {numero} em {tj_nome}...")

        # Acessar formulário
        driver.get(TJS[tj_nome])
        time.sleep(2)

        # Preencher número do processo via JavaScript
        driver.execute_script(f"""
            var campo = document.getElementById('numeroDigitoAnoUnificado');
            if (campo) campo.value = '{numero}';
        """)
        time.sleep(0.5)

        # Clicar buscar
        try:
            btn = driver.find_element(By.ID, "botaoConsultarProcessos")
            btn.click()
            time.sleep(3)
        except Exception:
            logger.debug(f"  ⚠️  Botão de busca não encontrado")
            pass

        # Procurar link "Visualizar autos"
        try:
            link = driver.find_element(By.ID, "linkPasta")
            href = link.get_attribute("href")
            link.click()
            time.sleep(2)

            # Procurar data de ofício no HTML
            html = driver.page_source
            datas = re.findall(r"(\d{2})/(\d{2})/(\d{4})", html)

            if datas:
                # Formato ISO
                data_oficio = f"{datas[0][2]}-{datas[0][1]}-{datas[0][0]}"
                logger.info(f"  ✅ Encontrado em {tj_nome}: {data_oficio}")
                return {
                    "numero": numero,
                    "tj": tj_nome,
                    "status": "encontrado",
                    "data_oficio": data_oficio,
                    "link_autos": href,
                }
            else:
                logger.info(f"  ⚠️  Autos encontrados mas sem data de ofício")
                return {
                    "numero": numero,
                    "tj": tj_nome,
                    "status": "nao_encontrado",
                    "data_oficio": None,
                    "link_autos": href,
                }
        except Exception as e:
            logger.debug(f"  ⚠️  Não encontrou autos: {e}")
            return {
                "numero": numero,
                "tj": tj_nome,
                "status": "nao_encontrado",
                "data_oficio": None,
                "link_autos": None,
            }

    except Exception as e:
        logger.error(f"  ❌ Erro: {e}")
        return {
            "numero": numero,
            "tj": tj_nome,
            "status": "erro",
            "data_oficio": None,
            "link_autos": None,
            "erro": str(e),
        }


def buscar_dados_projuris(numero_processo):
    """Busca dados complementares de processo na Projuris.

    Retorna: dict com titulo, partes, vara, etc. ou {} se não encontrar.
    """
    try:
        import httpx
        base_url = os.environ.get("PROJURIS_BASE_URL", "").rstrip("/")
        token = os.environ.get("PROJURIS_TOKEN", "")

        if not base_url or not token:
            logger.debug("Projuris não configurado, pulando busca")
            return {}

        with httpx.Client(timeout=10, headers={"Authorization": f"Bearer {token}"}) as client:
            # Buscar por número CNJ
            resp = client.get(f"{base_url}/processos", params={"numero": numero_processo})
            if resp.status_code == 200:
                corpo = resp.json()
                itens = corpo if isinstance(corpo, list) else corpo.get("itens") or corpo.get("content") or []
                if itens:
                    item = itens[0]
                    return {
                        "projuris_id": item.get("id"),
                        "titulo": item.get("titulo") or item.get("pasta"),
                        "autor": item.get("parteAtiva", {}).get("nome") if isinstance(item.get("parteAtiva"), dict) else item.get("parteAtiva"),
                        "reu": item.get("partePassiva", {}).get("nome") if isinstance(item.get("partePassiva"), dict) else item.get("partePassiva"),
                        "vara": item.get("vara"),
                        "tribunal": item.get("tribunal") or item.get("orgao"),
                        "juiz": item.get("juiz"),
                        "especialidade": item.get("area") or item.get("especialidade"),
                        "status": item.get("status"),
                    }
    except Exception as e:
        logger.debug(f"Erro ao buscar em Projuris: {e}")
    return {}


def buscar_intimacoes_completo(tribunal="TJMS"):
    """Executa a busca COMPLETA DE UMA VEZ (não 8h)."""
    try:
        from selenium import webdriver

        # Ler emails
        processos = ler_emails_intimacoes()
        if not processos:
            logger.error("❌ Nenhum processo encontrado nos emails")
            return {
                "status": "erro",
                "processos_encontrados": 0,
                "buscas": [],
                "erro": "Nenhum processo nos emails",
            }

        logger.info(f"🚀 Buscando {len(processos)} processos em {tribunal}...")

        resultados = {
            "data_execucao": datetime.utcnow().isoformat(),
            "tribunal": tribunal,
            "processos_encontrados": len(processos),
            "buscas": []
        }

        # Abrir navegador Opera (Mac) ou Chrome (Windows)
        options = webdriver.ChromeOptions()

        # Tenta usar Opera no Mac
        try:
            options.binary_location = "/Applications/Opera.app/Contents/MacOS/Opera"
        except:
            # Em Windows, usa Chrome padrão
            pass

        driver = webdriver.Chrome(options=options)

        try:
            # Buscar em TODOS os processos DE UMA VEZ (não loop 8h)
            for processo in processos:
                numero = processo["numero"]
                tj = processo.get("tj", tribunal)

                # Buscar dados complementares em Projuris
                dados_projuris = buscar_dados_projuris(numero)

                # Buscar em TJMS e TJMT (ambos)
                encontrou = False
                for tribunal_busca in ["TJMS", "TJMT"]:
                    resultado = buscar_processo_esaj(driver, numero, tribunal_busca)

                    # Anexar dados Projuris ao resultado
                    if dados_projuris:
                        resultado.update(dados_projuris)

                    resultados["buscas"].append(resultado)

                    # Se encontrou em um, não precisa buscar no outro
                    if resultado["status"] == "encontrado":
                        encontrou = True
                        break

        finally:
            driver.quit()
            logger.info("✅ Navegador fechado")

        logger.info(f"📊 Total de buscas: {len(resultados['buscas'])}")
        logger.info(f"📊 Encontrados: {sum(1 for b in resultados['buscas'] if b['status'] == 'encontrado')}")

        return resultados

    except Exception as e:
        logger.exception(f"❌ Erro na busca: {e}")
        return {
            "status": "erro",
            "processos_encontrados": 0,
            "buscas": [],
            "erro": str(e),
        }


def processar_job_esaj(db, job):
    """Processa um job de tipo 'esaj_intimacoes'.

    1. Marca como 'processando'
    2. Executa busca completa
    3. Salva resultado
    4. Marca como 'concluido' ou 'erro'
    """
    from app.models import Job
    from datetime import datetime as dt

    try:
        job.status = "processando"
        job.executor = "esaj_intimacoes_agent"
        job.iniciado_em = dt.utcnow()
        db.commit()

        # Executar busca
        resultado = buscar_intimacoes_completo(tribunal=job.payload.get("tribunal", "TJMS"))

        # Salvar resultado
        job.resultado = resultado
        job.status = "concluido"
        job.concluido_em = dt.utcnow()
        db.commit()

        logger.info(f"✅ Job {job.id} concluído")
        return True

    except Exception as e:
        logger.exception(f"❌ Erro no job {job.id}: {e}")
        job.status = "erro"
        job.erro = str(e)
        job.concluido_em = dt.utcnow()
        db.commit()
        return False


def main():
    """Loop infinito: poll jobs, processa."""
    import time
    from app.models import Job
    from app.services.database import SessionLocal

    logger.info("🔄 Agente ESAJ iniciado")

    while True:
        try:
            db = SessionLocal()
            try:
                # Buscar próximo job na fila
                job = db.query(Job).filter(
                    Job.tipo == "esaj_intimacoes",
                    Job.status == "na_fila"
                ).order_by(Job.id).first()

                if job:
                    logger.info(f"🎯 Processando job {job.id}")
                    processar_job_esaj(db, job)
                else:
                    logger.debug("⏳ Nenhum job na fila")

            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Erro no loop: {e}")

        # Aguardar 30s antes de próxima checagem
        time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    main()
