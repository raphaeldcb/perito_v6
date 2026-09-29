"""
Serviço: Download de autos TJMS via Playwright
Automação: Login → Consulta → Download PDF
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Importar Playwright (instalado no backend)
try:
    from playwright.async_api import async_playwright
except ImportError:
    logger.error("Playwright não instalado. Instale: pip install playwright")
    raise


class TJMSAutomation:
    """Automação de download de autos do TJMS e-SAJ"""

    def __init__(self, cpf: str, senha: str, output_dir: Path = None):
        self.cpf = cpf
        self.senha = senha
        self.output_dir = output_dir or Path.home() / "Downloads"
        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self, headless: bool = True):
        """Iniciar browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        logger.info("✅ Browser iniciado")

    async def login(self) -> bool:
        """Login: CPF + SENHA + 2FA (automático via email)"""
        try:
            logger.info("🔐 Iniciando login TJMS...")

            # 1. Navegar pra página de login
            await self.page.goto("https://esaj.tjms.jus.br/esaj")
            await self.page.wait_for_load_state("networkidle")
            logger.info("   ✓ Página de login carregada")

            # 2. Clicar em "Identificar-se"
            await self.page.click("text=Identificar-se")
            await self.page.wait_for_timeout(1000)
            logger.info("   ✓ Clicou em 'Identificar-se'")

            # 3. Preencher CPF
            await self.page.fill("input[id*='cpf'], input[name*='cpf']", self.cpf)
            logger.info(f"   ✓ Digitou CPF")

            # 4. Preencher SENHA
            await self.page.fill("input[type='password']", self.senha)
            logger.info(f"   ✓ Digitou SENHA")

            # 5. Clicar Entrar
            await self.page.click("button:has-text('Entrar'), button:has-text('Acessar')")
            logger.info("   ✓ Clicou em 'Entrar'")

            # 6. Aguardar 2FA e extrair código do email
            logger.info("   ⏳ Aguardando código 2FA...")
            await self.page.wait_for_timeout(3000)

            # Tentar extrair código 2FA do email
            codigo_2fa = await self._extrair_codigo_2fa()
            if not codigo_2fa:
                logger.error("   ❌ Código 2FA não encontrado")
                return False

            logger.info(f"   ✅ Código 2FA extraído: {codigo_2fa}")

            # 7. Digitar código 2FA
            await self.page.fill("input[name*='codigo'], input[id*='2fa']", codigo_2fa)
            logger.info(f"   ✓ Digitou código 2FA")

            # 8. Confirmar
            await self.page.click("button:has-text('Validar'), button:has-text('OK')")
            await self.page.wait_for_load_state("networkidle")

            logger.info("✅ Login bem-sucedido!")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            return False

    async def _extrair_codigo_2fa(self) -> str | None:
        """Extrair código 2FA do email via Graph API"""
        try:
            # Importar função do backend (se disponível)
            from app.services.graph_mail import buscar_codigo_2fa

            desde = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"
            codigo = buscar_codigo_2fa(desde_iso=desde)
            return codigo
        except:
            logger.warning("⚠️ Não foi possível extrair código 2FA do email")
            return None

    async def consultar_e_baixar(self, cnj: str) -> Path | None:
        """Consultar processo e baixar autos"""
        try:
            logger.info(f"📋 Consultando processo: {cnj}")

            # 1. Navegar pra consulta
            await self.page.goto("https://esaj.tjms.jus.br/cpopg5/open.do")
            await self.page.wait_for_load_state("networkidle")
            logger.info("   ✓ Página de consulta carregada")

            # 2. Preencher CNJ
            inputs = await self.page.query_selector_all("input[type='text']")
            if inputs:
                await inputs[0].fill(cnj)
            logger.info(f"   ✓ Digitou CNJ: {cnj}")

            # 3. Buscar
            await self.page.click("button:has-text('Pesquisar'), button:has-text('Buscar')")
            await self.page.wait_for_load_state("networkidle")
            logger.info("   ✓ Pesquisou processo")

            # 4. Clicar no processo
            await self.page.click(f"text={cnj}")
            await self.page.wait_for_load_state("networkidle")
            logger.info(f"   ✓ Processo {cnj} aberto")

            # 5. Aguardar Pasta Digital
            await self.page.wait_for_timeout(2000)

            # 6. Clicar em "Baixar"
            logger.info("📥 Iniciando download...")
            await self.page.click("a:has-text('Baixar PDF'), button:has-text('Baixar')")
            await self.page.wait_for_timeout(2000)
            logger.info("   ✓ Clicou em download")

            # 7. Aguardar PDF ser gerado
            self.output_dir.mkdir(parents=True, exist_ok=True)

            async with self.page.expect_download() as download_info:
                await self.page.wait_for_timeout(10000)

            download = await download_info.value
            output_path = self.output_dir / download.suggested_filename
            await download.save_as(output_path)

            logger.info(f"✅ PDF baixado: {output_path}")
            logger.info(f"   Tamanho: {output_path.stat().st_size / 1024:.1f} KB")

            return output_path

        except Exception as e:
            logger.error(f"❌ Erro ao consultar/baixar: {e}")
            return None

    async def close(self):
        """Fechar browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser fechado")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Função wrapper para uso síncrono
def download_autos_tjms(cpf: str, senha: str, cnj: str) -> Path | None:
    """Wrapper síncrono para download de autos"""
    async def _async():
        async with TJMSAutomation(cpf, senha) as automation:
            if await automation.login():
                return await automation.consultar_e_baixar(cnj)
            return None

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_async())
    except Exception as e:
        logger.error(f"Erro ao baixar autos: {e}")
        return None
