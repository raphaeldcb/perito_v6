"""
Serviço de Geração e Salvamento de Laudo Forense.

Orquestra o pipeline completo:
1. Extrai dados de ForensicAnalysis via ForensicAnalysisToLaudoData
2. Gera DOCX via ForensicLaudoDocxGenerator
3. Converte DOCX → PDF via ForensicDocxToPdf
4. Salva ambos os arquivos no OneDrive (async)
5. Retorna URLs e metadados para download

Task 3: End-to-End Laudo Generation Service
"""
import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional
import requests

from app.services.forensic_analysis_to_laudo_data import ForensicAnalysisToLaudoData
from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator
from app.services.forensic_docx_to_pdf import ForensicDocxToPdf

logger = logging.getLogger(__name__)

# Azure/Graph API configuration
TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
ONEDRIVE_FOLDER_PATH = os.getenv(
    "ONEDRIVE_FOLDER_PATH",
    "/drive/root:/IPCMS - ARQUIVOS"
)

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

# Token cache
_token_cache = {"token": None, "expira": 0}


class ForensicLaudoService:
    """
    Serviço que orquestra a geração e salvamento de laudos forenses.

    Métodos principais:
    - async generate_and_save(analysis, user_name=None) -> Dict[str, str]
        Pipeline completo: extract → generate → convert → save → return URLs

    - async _save_to_onedrive(file_bytes, filepath) -> str
        Salva arquivo no OneDrive usando Graph API (async wrapper)
    """

    def __init__(self):
        """Inicializa o serviço com as dependências necessárias."""
        self.extractor = ForensicAnalysisToLaudoData()
        self.docx_generator = ForensicLaudoDocxGenerator()
        try:
            self.pdf_converter = ForensicDocxToPdf()
        except FileNotFoundError as e:
            logger.warning(f"PDF converter initialization failed (LibreOffice not found): {e}")
            self.pdf_converter = None

    async def generate_and_save(
        self,
        analysis: "ForensicAnalysis",
        user_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Pipeline completo de geração e salvamento de laudo.

        Etapas:
        1. Extrai dados de ForensicAnalysis
        2. Gera DOCX preenchido
        3. Converte DOCX → PDF
        4. Salva ambos no OneDrive
        5. Retorna URLs e metadados

        Args:
            analysis: Objeto ForensicAnalysis com resultados da análise
            user_name: Nome do perito/contratante (opcional)

        Returns:
            Dict com:
            - docx_url: URL pública do DOCX no OneDrive
            - pdf_url: URL pública do PDF no OneDrive
            - filename: Nome base do arquivo (sem extensão)
            - codigo_laudo: Código identificador do laudo

        Raises:
            Exception: Se alguma etapa falhar (com logging detalhado)
        """
        try:
            # Step 1: Extract data
            logger.info(f"[Laudo Gen] Extracting data from ForensicAnalysis {analysis.id}...")
            laudo_data = self.extractor.extract(analysis, user_name=user_name)
            codigo_laudo = laudo_data.get('codigo_laudo', 'L00000000UNKNOWN')
            logger.info(f"[Laudo Gen] Extraction complete. Codigo: {codigo_laudo}")

            # Step 2: Generate DOCX
            logger.info(f"[Laudo Gen] Generating DOCX...")
            docx_bytes = self.docx_generator.generate(laudo_data)
            logger.info(f"[Laudo Gen] DOCX generated: {len(docx_bytes)} bytes")

            # Step 3: Convert to PDF
            pdf_bytes = None
            if self.pdf_converter:
                try:
                    logger.info(f"[Laudo Gen] Converting DOCX → PDF...")
                    pdf_bytes = self.pdf_converter.convert(docx_bytes)
                    logger.info(f"[Laudo Gen] PDF generated: {len(pdf_bytes)} bytes")
                except Exception as e:
                    logger.error(f"[Laudo Gen] PDF conversion failed: {e}. Continuing without PDF.")
                    pdf_bytes = None
            else:
                logger.warning("[Laudo Gen] PDF converter not available. Skipping PDF generation.")

            # Step 4: Prepare OneDrive paths
            base_filename = self._generate_filename(codigo_laudo)
            docx_onedrive_path = self._generate_onedrive_path(base_filename, "docx")
            pdf_onedrive_path = self._generate_onedrive_path(base_filename, "pdf") if pdf_bytes else None

            # Step 5: Save to OneDrive (async)
            logger.info(f"[Laudo Gen] Saving DOCX to OneDrive: {docx_onedrive_path}")
            docx_url = await self._save_to_onedrive(docx_bytes, docx_onedrive_path)
            logger.info(f"[Laudo Gen] DOCX saved: {docx_url}")

            pdf_url = None
            if pdf_bytes:
                logger.info(f"[Laudo Gen] Saving PDF to OneDrive: {pdf_onedrive_path}")
                pdf_url = await self._save_to_onedrive(pdf_bytes, pdf_onedrive_path)
                logger.info(f"[Laudo Gen] PDF saved: {pdf_url}")

            # Step 6: Build result
            result = {
                'docx_url': docx_url,
                'pdf_url': pdf_url or '',
                'filename': base_filename,
                'codigo_laudo': codigo_laudo,
            }

            logger.info(f"[Laudo Gen] Pipeline complete for {codigo_laudo}")
            return result

        except Exception as e:
            logger.error(f"[Laudo Gen] Pipeline failed: {e}", exc_info=True)
            raise

    async def _save_to_onedrive(self, file_bytes: bytes, filepath: str) -> str:
        """
        Salva arquivo no OneDrive usando Graph API (async wrapper).

        Args:
            file_bytes: Conteúdo do arquivo em bytes
            filepath: Caminho no OneDrive, ex: /Laudos/2026/agosto/Laudo_L...

        Returns:
            str: URL pública do arquivo salvo

        Raises:
            Exception: Se o upload falhar
        """
        # Usar asyncio.to_thread para fazer I/O assincronamente
        return await asyncio.to_thread(self._save_to_onedrive_sync, file_bytes, filepath)

    def _save_to_onedrive_sync(self, file_bytes: bytes, filepath: str) -> str:
        """
        Implementação síncrona do salvamento no OneDrive.
        Chamada via asyncio.to_thread para não bloquear event loop.

        Args:
            file_bytes: Conteúdo do arquivo
            filepath: Caminho no OneDrive

        Returns:
            URL pública do arquivo
        """
        try:
            # Obter token
            token = self._get_graph_token()

            # Montar URL do upload
            # Formato: PUT /me/drive/root:/{path to file}:/content
            upload_endpoint = f"/me/drive/root:{filepath}:/content"
            upload_url = f"{GRAPH_API_URL}{upload_endpoint}"

            logger.debug(f"Uploading to: {upload_url}")

            # Fazer upload
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            }

            response = requests.put(
                upload_url,
                data=file_bytes,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            # Parse response to get the webUrl
            result = response.json()
            web_url = result.get('webUrl', '')

            if not web_url:
                logger.warning(f"No webUrl in response: {result}")
                # Fallback: construct URL from path
                web_url = f"https://onedrive.live.com/file{filepath}"

            logger.info(f"[OneDrive Upload] Success: {filepath} → {web_url}")
            return web_url

        except Exception as e:
            logger.error(f"[OneDrive Upload] Failed for {filepath}: {e}", exc_info=True)
            raise

    def _get_graph_token(self) -> str:
        """
        Obtém token de acesso ao Microsoft Graph (com cache).

        Returns:
            str: Token de acesso válido

        Raises:
            RuntimeError: Se falhar ao obter o token
        """
        # Verificar cache
        if _token_cache["token"] and time.time() < _token_cache["expira"] - 60:
            logger.debug("[Graph Token] Using cached token")
            return _token_cache["token"]

        logger.debug("[Graph Token] Requesting new token from Azure...")

        try:
            response = requests.post(
                TOKEN_ENDPOINT,
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
                timeout=30
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"[Graph Token] Failed to obtain token: {e}")

        body = response.json()
        if "access_token" not in body:
            error_desc = body.get("error_description", str(body)[:300])
            raise RuntimeError(f"[Graph Token] Invalid response: {error_desc}")

        token = body["access_token"]
        expires_in = int(body.get("expires_in", 3600))

        _token_cache["token"] = token
        _token_cache["expira"] = time.time() + expires_in

        logger.debug(f"[Graph Token] New token obtained, expires in {expires_in}s")
        return token

    def _generate_filename(self, codigo_laudo: str) -> str:
        """
        Gera nome base do arquivo (sem extensão).

        Formato: Laudo_L{codigo}_{YYYYMMDD_HHMMSS}

        Args:
            codigo_laudo: Código do laudo, ex: L2026080700003039

        Returns:
            Nome base, ex: Laudo_L2026080700003039_20260807_140000
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"Laudo_{codigo_laudo}_{timestamp}"
        return filename

    def _generate_onedrive_path(self, base_filename: str, extension: str) -> str:
        """
        Gera caminho completo no OneDrive.

        Formato: /Laudos/{YYYY}/{month_name}/{base_filename}.{extension}

        Exemplo:
            /Laudos/2026/agosto/Laudo_L2026080700003039_20260807_140000.docx

        Args:
            base_filename: Nome base sem extensão
            extension: Extensão (docx, pdf)

        Returns:
            Caminho completo no OneDrive
        """
        now = datetime.utcnow()
        year = now.strftime("%Y")

        # Month names in Portuguese
        month_names = {
            1: "janeiro",
            2: "fevereiro",
            3: "marco",
            4: "abril",
            5: "maio",
            6: "junho",
            7: "julho",
            8: "agosto",
            9: "setembro",
            10: "outubro",
            11: "novembro",
            12: "dezembro",
        }
        month = month_names.get(now.month, "dezembro")

        path = f"/Laudos/{year}/{month}/{base_filename}.{extension}"
        return path
