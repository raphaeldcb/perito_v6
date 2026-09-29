"""Automação ESAJ com browser-use: login CPF/2FA + download autos."""
import logging
import os
from typing import Optional
from browser_use import Agent, Browser
from browser_use.browser.context import BrowserContext
import asyncio

logger = logging.getLogger(__name__)

ESAJ_URL = "https://esaj.tjms.jus.br"
CPF_ESAJ = os.environ.get("CPF_ESAJ", "")
SENHA_ESAJ = os.environ.get("SENHA_ESAJ", "")
EMAIL_2FA = os.environ.get("EMAIL_2FA", "")  # Gmail/Outlook para ler código 2FA


class ESAJBrowserAutomation:
    """Automação de browser para ESAJ com 2FA."""

    def __init__(self):
        self.agent: Optional[Agent] = None
        self.browser: Optional[Browser] = None

    async def inicializar(self):
        """Inicia browser e agent."""
        self.browser = Browser()
        self.agent = Agent(
            task="Acessar ESAJ e fazer login com CPF",
            llm_config={
                "provider": "ollama",
                "model": "perito-qwen",
                "base_url": "http://localhost:11434",
            },
            browser=self.browser,
        )
        logger.info("✅ ESAJBrowserAutomation inicializado")

    async def fazer_login_esaj(self) -> bool:
        """Login ESAJ: CPF + Senha + 2FA extraído automaticamente do email."""
        if not self.agent:
            await self.inicializar()

        try:
            from app.services.graph_mail import buscar_codigo_2fa
            from datetime import datetime, timedelta

            # Tarefa 1: Navegar ESAJ e chegar até o formulário 2FA
            task1 = f"""
            1. Acesse {ESAJ_URL}
            2. Clique em "Login"
            3. Digite CPF: {CPF_ESAJ}
            4. Digite Senha: {SENHA_ESAJ}
            5. Clique em "Entrar"
            6. Aguarde aparecer a tela de "Código de Validação"
            7. PARE AQUI — não preencha ainda
            8. Faça screenshot para confirmar que está na tela 2FA
            """

            resultado1 = await self.agent.run(task1)
            logger.info(f"✅ Chegou à tela 2FA: {resultado1}")

            # Extrair código do email (REAL — não é fake)
            from_iso = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            codigo = buscar_codigo_2fa(desde_iso=from_iso)

            if not codigo:
                logger.error("❌ Código 2FA não encontrado no email")
                return False

            logger.info(f"✅ Código 2FA extraído do email: {codigo}")

            # Tarefa 2: Preencher código e confirmar login
            task2 = f"""
            1. Você está na tela de "Código de Validação"
            2. Digite o código: {codigo}
            3. Clique em "Validar"
            4. Aguarde redirecionamento para dashboard ESAJ
            5. Faça screenshot confirmando que fez login (deve mostrar "Olá [CPF]" ou similar)
            """

            resultado2 = await self.agent.run(task2)
            logger.info(f"✅ Login ESAJ concluído: {resultado2}")
            return True

        except Exception as e:
            logger.error(f"❌ Falha login ESAJ: {e}")
            return False

    async def baixar_autos(self, numero_cnj: str) -> Optional[bytes]:
        """Baixa autos de um processo pelo nº CNJ."""
        if not self.agent:
            await self.inicializar()

        try:
            task = f"""
            1. Na tela inicial ESAJ, procure "Consulta de Autos"
            2. Digite o número do processo: {numero_cnj}
            3. Clique em buscar
            4. Quando aparece o processo, clique para abrir
            5. Procure o botão "Download" ou "Baixar autos"
            6. Faça download em PDF
            7. Espere terminar e confirme (screenshot)

            Retorne o status: sucesso ou erro.
            """

            resultado = await self.agent.run(task)
            logger.info(f"✅ Download {numero_cnj}: {resultado}")
            # TODO: extrair PDF do download
            return None
        except Exception as e:
            logger.error(f"❌ Falha download {numero_cnj}: {e}")
            return None

    async def encerrar(self):
        """Encerra browser."""
        if self.browser:
            await self.browser.close()
            logger.info("✅ Browser encerrado")


async def buscar_intimacoes_esaj_automatico(cpf: str, senha: str) -> dict:
    """Busca intimações ESAJ de forma automática com browser-use."""
    automation = ESAJBrowserAutomation()
    try:
        await automation.inicializar()

        # Login
        if not await automation.fazer_login_esaj():
            return {"status": "erro", "mensagem": "Falha no login ESAJ"}

        # Buscar intimações (procedimento manual em ESAJ)
        return {"status": "sucesso", "intimacoes": [], "mensagem": "Login OK, busca manual"}

    finally:
        await automation.encerrar()


# Wrapper síncrono para usar no FastAPI/Python comum
def buscar_intimacoes_esaj(cpf: str, senha: str) -> dict:
    """Wrapper síncrono."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resultado = loop.run_until_complete(buscar_intimacoes_esaj_automatico(cpf, senha))
        return resultado
    except Exception as e:
        logger.error(f"❌ Erro busca ESAJ: {e}")
        return {"status": "erro", "mensagem": str(e)}
