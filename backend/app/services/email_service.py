"""
EmailService — Email notification for intimação processing.

Sends HTML emails via Gmail SMTP with exponential backoff retry logic.
Uses Python stdlib only (smtplib, email.mime, asyncio, logging).

Configuration via environment variables:
- SMTP_HOST: SMTP server host (default: smtp.gmail.com)
- SMTP_PORT: SMTP server port (default: 587)
- SMTP_USER: SMTP username (e.g., ipcms@ipcms.com.br)
- SMTP_PASS: SMTP password (app-specific password for Gmail)
- SMTP_FROM: From address (e.g., ipcms@ipcms.com.br)
- SMTP_TIMEOUT: Connection timeout in seconds (default: 10)
- EMAIL_ADMIN: Admin email for alerts (e.g., bruno@ipcms.com.br)
- EMAIL_DEBUG: Print email instead of sending (default: false)
"""

import asyncio
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send email notifications with retry logic."""

    # Retry configuration
    MAX_RETRIES = 5
    BACKOFF_SEQUENCE = [1, 2, 4, 8, 16]  # seconds

    def __init__(self):
        """Initialize EmailService with configuration from environment."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.smtp_from = os.getenv("SMTP_FROM", "ipcms@ipcms.com.br")
        self.smtp_timeout = int(os.getenv("SMTP_TIMEOUT", "10"))
        self.email_admin = os.getenv("EMAIL_ADMIN", "")
        self.email_debug = os.getenv("EMAIL_DEBUG", "false").lower() == "true"

    async def enviar_notificacao(self, usuario_id: int, analise: dict) -> bool:
        """
        Send email notification for processed intimação.

        Args:
            usuario_id: User ID (for logging and future DB lookup)
            analise: Dict with intimação analysis data:
                - arquivo: filename
                - confianca: confidence percentage (0-100)
                - tipo_pericia: type of expertise (Contábil, DNA, Eng, etc)
                - setor: sector code (10=Contábil, 20=DNA, etc)
                - riscos: risk level (Baixo, Médio, Alto)
                - campos_extraidos: dict of extracted fields

        Returns:
            bool: True if email sent successfully, False if failed after all retries
        """
        subject = self._mount_email_subject(analise)
        html_body = self._mount_html_email(analise)
        to_email = self.smtp_from  # TODO: Fetch user email from DB using usuario_id

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self._send_smtp(to_email, subject, html_body)
                logger.info(
                    f"✅ Email enviado para usuário {usuario_id} | "
                    f"arquivo: {analise.get('arquivo', 'unknown')} | "
                    f"tentativa: {attempt}"
                )
                return True

            except smtplib.SMTPAuthenticationError as e:
                # Critical error — don't retry
                logger.error(
                    f"❌ Email falhou — autenticação SMTP | "
                    f"usuário {usuario_id} | erro: {e}"
                )
                await self._notify_admin_critical(usuario_id, analise, str(e))
                return False

            except (smtplib.SMTPException, ConnectionRefusedError, OSError, TimeoutError) as e:
                # Transient error — retry
                last_error = e
                if attempt < self.MAX_RETRIES:
                    backoff = self.BACKOFF_SEQUENCE[attempt - 1]
                    logger.warning(
                        f"⚠️ Email falhou — tentativa {attempt}/{self.MAX_RETRIES} | "
                        f"aguardando {backoff}s | erro: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"❌ Email falhou após {self.MAX_RETRIES} tentativas | "
                        f"usuário {usuario_id} | arquivo: {analise.get('arquivo', 'unknown')} | "
                        f"erro: {e}"
                    )
                    await self._notify_admin_critical(usuario_id, analise, str(e))
                    return False

            except Exception as e:
                # Unknown error — don't retry
                logger.error(
                    f"❌ Email falhou — erro desconhecido | "
                    f"usuário {usuario_id} | erro: {type(e).__name__}: {e}"
                )
                await self._notify_admin_critical(usuario_id, analise, str(e))
                return False

        return False

    def _mount_email_subject(self, analise: dict) -> str:
        """
        Mount email subject line.

        Args:
            analise: Analysis dict

        Returns:
            str: Email subject
        """
        arquivo = analise.get("arquivo", "documento")
        return f"✅ Intimação Processada — {arquivo}"

    def _mount_html_email(self, analise: dict) -> str:
        """
        Mount HTML email body with analysis data.

        Args:
            analise: Analysis dict with arquivo, confianca, tipo_pericia, etc.

        Returns:
            str: HTML email body
        """
        arquivo = analise.get("arquivo", "desconhecido")
        confianca = analise.get("confianca", 0)
        tipo_pericia = analise.get("tipo_pericia", "Não determinado")
        setor = analise.get("setor", "Não determinado")
        riscos = analise.get("riscos", "Não determinado")
        campos_extraidos = analise.get("campos_extraidos", {})

        # Build campos table HTML
        campos_table_html = ""
        if campos_extraidos:
            for campo, valor in campos_extraidos.items():
                campos_table_html += f"""
            <tr>
              <td><strong>{campo}</strong></td>
              <td>{valor}</td>
            </tr>
            """

        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f5f5f5;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: auto;
      padding: 20px;
      background-color: #ffffff;
    }}
    .header {{
      background-color: #2196F3;
      color: white;
      padding: 20px;
      border-radius: 4px 4px 0 0;
      text-align: center;
    }}
    .header h2 {{
      margin: 0;
      font-size: 20px;
    }}
    .content {{
      border: 1px solid #ddd;
      padding: 20px;
      border-radius: 0 0 4px 4px;
    }}
    .field {{
      margin-bottom: 15px;
      line-height: 1.6;
    }}
    .field-label {{
      font-weight: bold;
      color: #333;
    }}
    .field-value {{
      color: #666;
      margin-left: 10px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 15px;
      margin-bottom: 15px;
    }}
    th {{
      background-color: #f5f5f5;
      padding: 12px;
      text-align: left;
      font-weight: bold;
      border-bottom: 2px solid #ddd;
    }}
    td {{
      padding: 10px 12px;
      border-bottom: 1px solid #eee;
    }}
    tr:hover {{
      background-color: #f9f9f9;
    }}
    .footer {{
      color: #999;
      font-size: 12px;
      text-align: center;
      margin-top: 20px;
      border-top: 1px solid #eee;
      padding-top: 10px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>✅ Intimação Processada</h2>
    </div>
    <div class="content">
      <div class="field">
        <span class="field-label">Arquivo:</span>
        <span class="field-value">{arquivo}</span>
      </div>
      <div class="field">
        <span class="field-label">Confiança:</span>
        <span class="field-value">{confianca}%</span>
      </div>
      <div class="field">
        <span class="field-label">Tipo de Perícia:</span>
        <span class="field-value">{tipo_pericia}</span>
      </div>
      <div class="field">
        <span class="field-label">Setor:</span>
        <span class="field-value">{setor}</span>
      </div>
      <div class="field">
        <span class="field-label">Riscos:</span>
        <span class="field-value">{riscos}</span>
      </div>

      <h3 style="color: #333; margin-top: 25px; margin-bottom: 10px;">Campos Extraídos</h3>
      <table>
        <thead>
          <tr>
            <th>Campo</th>
            <th>Valor</th>
          </tr>
        </thead>
        <tbody>
          {campos_table_html or '<tr><td colspan="2" style="text-align: center; color: #999;">Nenhum campo extraído</td></tr>'}
        </tbody>
      </table>

      <div class="footer">
        Processado em: {timestamp}
      </div>
    </div>
  </div>
</body>
</html>
        """
        return html.strip()

    def _send_smtp(self, to_email: str, subject: str, html_body: str) -> None:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body

        Raises:
            smtplib.SMTPException: On SMTP errors
            ConnectionRefusedError: On connection errors
            OSError: On OS-level errors
        """
        if self.email_debug:
            logger.debug(f"📧 [DEBUG MODE] Email: To={to_email} Subject={subject}")
            return

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_from
        msg["To"] = to_email

        # Attach HTML body
        msg.attach(MIMEText(html_body, "html"))

        # Connect and send
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.smtp_timeout) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)

    async def _notify_admin_critical(
        self, usuario_id: int, analise: dict, error_msg: str
    ) -> None:
        """
        Notify admin when email fails after all retries.

        Args:
            usuario_id: User ID affected
            analise: Analysis dict
            error_msg: Error message from last attempt
        """
        if not self.email_admin:
            logger.warning("⚠️ EMAIL_ADMIN não configurado — notificação não enviada")
            return

        admin_subject = f"🚨 ALERTA: Email falhou para usuário {usuario_id}"
        admin_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
  <h2>🚨 Alerta: Email Falhou</h2>
  <p><strong>Usuário:</strong> {usuario_id}</p>
  <p><strong>Arquivo:</strong> {analise.get('arquivo', 'desconhecido')}</p>
  <p><strong>Tipo de Perícia:</strong> {analise.get('tipo_pericia', 'desconhecido')}</p>
  <p><strong>Erro:</strong> <code>{error_msg}</code></p>
  <p><strong>Timestamp:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
  <p>Verifique os logs do backend para mais detalhes.</p>
</body>
</html>
        """

        try:
            self._send_smtp(self.email_admin, admin_subject, admin_body)
            logger.info(f"✅ Notificação crítica enviada ao admin: {self.email_admin}")
        except Exception as e:
            logger.error(f"❌ Falha ao notificar admin: {e}")
