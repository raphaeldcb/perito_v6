# Email SMTP Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Gmail SMTP email service from Perito System (Node.js) to Perito v6 (FastAPI), enabling email notifications when intimações are processed.

**Architecture:** EmailService class (Python stdlib `smtplib`) with exponential backoff retry logic (5 attempts), integrated into IntimacaoService workflow. Non-blocking: email failures don't halt intimação processing. Admin alerts on critical failures.

**Tech Stack:** 
- FastAPI (existing)
- Python `smtplib` + `email.mime` (stdlib)
- Gmail SMTP (smtp.gmail.com:587, TLS)
- Environment variables for credentials

---

## Global Constraints

- **Python Version:** 3.11+ (already used in v6)
- **No new dependencies:** Use only Python stdlib (`smtplib`, `email`, `asyncio`, `logging`)
- **Configuration:** Via `.env` (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, EMAIL_ADMIN)
- **Authentication:** App-specific password (generated in Google Account)
- **Retry Strategy:** Max 5 attempts with backoff [1s, 2s, 4s, 8s, 16s]
- **Error Handling:** Log all errors; send admin alert on critical failure; don't block intimação processing
- **Testing:** Unit tests with mock SMTP; E2E tests on VPS with real Gmail

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── email_service.py          [NEW] EmailService class with SMTP + retry logic
│   │   └── intimacao_service.py      [MODIFY] Add EmailService call after processing
│   └── models/
│       └── notificacao.py            [VERIFY EXISTS] Schema for notification logging
├── tests/
│   ├── test_email_service.py         [NEW] Unit tests (mock SMTP)
│   └── test_intimacao_with_email.py  [NEW] Integration tests (email sending)
└── .env.example                      [MODIFY] Add SMTP_* variables
```

---

## Task 1: Create EmailService Class (Core)

**Files:**
- Create: `backend/app/services/email_service.py`
- Test: `backend/tests/test_email_service.py`

**Interfaces:**
- Consumes: Environment variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `EMAIL_ADMIN`)
- Produces: `EmailService` class with `async def enviar_notificacao(usuario_id: int, analise: dict) -> bool`

- [ ] **Step 1: Create test file with failing test for basic send**

Create `backend/tests/test_email_service.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.email_service import EmailService


@pytest.fixture
def email_service():
    """Fixture for EmailService with mock config"""
    with patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USER': 'test@gmail.com',
        'SMTP_PASS': 'testpass',
        'SMTP_FROM': 'test@gmail.com',
        'EMAIL_ADMIN': 'admin@example.com',
        'SMTP_TIMEOUT': '10'
    }):
        return EmailService()


@pytest.mark.asyncio
async def test_enviar_notificacao_success(email_service):
    """Test successful email send on first attempt"""
    analise = {
        'arquivo': 'test_intimacao.pdf',
        'confianca': 95,
        'tipo_pericia': 'Contábil',
        'setor': 10,
        'riscos': 'Médio',
        'campos_extraidos': {'numero_processo': '0001234-56.2026'}
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_instance
        
        result = await email_service.enviar_notificacao(usuario_id=1, analise=analise)
        
        assert result == True
        mock_instance.sendmail.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_email_service.py::test_enviar_notificacao_success -v
```

Expected output: `FAILED ... ModuleNotFoundError: No module named 'app.services.email_service'`

- [ ] **Step 3: Write EmailService implementation**

Create `backend/app/services/email_service.py`:

```python
"""Email service for sending SMTP notifications via Gmail."""

import asyncio
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Gmail SMTP with retry logic."""
    
    def __init__(self):
        """Initialize SMTP configuration from environment variables."""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')
        self.smtp_from = os.getenv('SMTP_FROM', 'ipcms@ipcms.com.br')
        self.smtp_timeout = int(os.getenv('SMTP_TIMEOUT', 10))
        self.email_admin = os.getenv('EMAIL_ADMIN', 'bruno@ipcms.com.br')
        self.email_debug = os.getenv('EMAIL_DEBUG', 'false').lower() == 'true'
        
        self.max_retries = 5
        self.retry_backoff = [1, 2, 4, 8, 16]  # seconds
    
    async def enviar_notificacao(
        self,
        usuario_id: int,
        analise: dict
    ) -> bool:
        """
        Send email notification for processed intimação.
        
        Args:
            usuario_id: User ID
            analise: Dict with intimação analysis data
                - arquivo: str (filename)
                - confianca: int (0-100)
                - tipo_pericia: str
                - setor: int
                - riscos: str
                - campos_extraidos: dict
        
        Returns:
            bool: True if sent successfully, False if failed after all retries
        """
        for tentativa in range(self.max_retries):
            try:
                # In a real implementation, fetch user email from DB
                # For now, assume it's passed or use a test email
                usuario_email = 'bruno@ipcms.com.br'  # TODO: fetch from DB
                
                html = self._montar_html(analise)
                
                await self._enviar_smtp(usuario_email, html, analise.get('arquivo', 'Documento'))
                
                logger.info(f"✅ Email enviado para usuário {usuario_id} | {analise.get('arquivo', 'N/A')}")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"❌ Erro autenticação SMTP: {e}")
                return False
            except smtplib.SMTPException as e:
                if tentativa < self.max_retries - 1:
                    backoff_time = self.retry_backoff[tentativa]
                    logger.warning(
                        f"⚠️ Email falhou, tentativa {tentativa + 1}/{self.max_retries} | "
                        f"aguardando {backoff_time}s | erro: {e}"
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                else:
                    logger.error(
                        f"❌ Email falhou após {self.max_retries} tentativas | "
                        f"usuário {usuario_id} | erro: {e}"
                    )
                    return False
            except Exception as e:
                logger.error(f"❌ Erro desconhecido ao enviar email: {e}")
                return False
        
        return False
    
    def _montar_html(self, analise: dict) -> str:
        """Mount HTML email with intimação data."""
        arquivo = analise.get('arquivo', 'Documento')
        confianca = analise.get('confianca', 0)
        tipo_pericia = analise.get('tipo_pericia', 'N/A')
        setor = analise.get('setor', 'N/A')
        riscos = analise.get('riscos', 'N/A')
        campos = analise.get('campos_extraidos', {})
        
        # Build campos table
        campos_html = ''
        for chave, valor in campos.items():
            campos_html += f'''
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{chave}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{valor or '-'}</td>
            </tr>
            '''
        
        html = f'''
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #2196F3; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                    .content {{ border: 1px solid #ddd; padding: 20px; border-radius: 0 0 5px 5px; }}
                    .info-box {{ margin: 15px 0; }}
                    .info-box strong {{ color: #2196F3; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                    th {{ background: #f5f5f5; padding: 10px; text-align: left; font-weight: bold; }}
                    .timestamp {{ color: #999; font-size: 12px; margin-top: 15px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>✅ Intimação Processada</h2>
                    </div>
                    <div class="content">
                        <div class="info-box">
                            <strong>Arquivo:</strong> {arquivo}
                        </div>
                        <div class="info-box">
                            <strong>Confiança:</strong> {confianca}%
                        </div>
                        <div class="info-box">
                            <strong>Tipo de Perícia:</strong> {tipo_pericia}
                        </div>
                        <div class="info-box">
                            <strong>Setor:</strong> {setor}
                        </div>
                        <div class="info-box">
                            <strong>Riscos:</strong> {riscos}
                        </div>
                        
                        <h3>Campos Extraídos</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Campo</th>
                                    <th>Valor</th>
                                </tr>
                            </thead>
                            <tbody>
                                {campos_html or '<tr><td colspan="2">Nenhum campo extraído</td></tr>'}
                            </tbody>
                        </table>
                        
                        <div class="timestamp">
                            Processado em: {self._get_timestamp()}
                        </div>
                    </div>
                </div>
            </body>
        </html>
        '''
        return html
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in BR format."""
        from datetime import datetime
        return datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    async def _enviar_smtp(self, destinatario: str, html: str, assunto_arquivo: str) -> None:
        """Send email via SMTP."""
        if self.email_debug:
            logger.info(f"[DEBUG] Email para {destinatario}: {assunto_arquivo}")
            return
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'✅ Intimação Processada: {assunto_arquivo}'
        msg['From'] = self.smtp_from
        msg['To'] = destinatario
        
        # Attach HTML
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.smtp_timeout) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.smtp_from, [destinatario], msg.as_string())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/test_email_service.py::test_enviar_notificacao_success -v
```

Expected output: `PASSED`

- [ ] **Step 5: Add test for retry logic**

Add to `backend/tests/test_email_service.py`:

```python
@pytest.mark.asyncio
async def test_enviar_notificacao_retry_on_failure(email_service):
    """Test retry logic: fails once, succeeds on second attempt"""
    analise = {
        'arquivo': 'test_intimacao.pdf',
        'confianca': 95,
        'tipo_pericia': 'Contábil',
        'setor': 10,
        'riscos': 'Médio',
        'campos_extraidos': {}
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        # Fail on first call, succeed on second
        mock_instance.sendmail.side_effect = [
            smtplib.SMTPException('Temporary error'),
            None  # Success
        ]
        mock_smtp.return_value.__enter__.return_value = mock_instance
        
        result = await email_service.enviar_notificacao(usuario_id=1, analise=analise)
        
        assert result == True
        assert mock_instance.sendmail.call_count == 2


@pytest.mark.asyncio
async def test_enviar_notificacao_fails_after_max_retries(email_service):
    """Test that email returns False after 5 retries"""
    analise = {
        'arquivo': 'test_intimacao.pdf',
        'confianca': 95,
        'tipo_pericia': 'Contábil',
        'setor': 10,
        'riscos': 'Médio',
        'campos_extraidos': {}
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        # Always fail
        mock_instance.sendmail.side_effect = smtplib.SMTPException('Persistent error')
        mock_smtp.return_value.__enter__.return_value = mock_instance
        
        result = await email_service.enviar_notificacao(usuario_id=1, analise=analise)
        
        assert result == False
        assert mock_instance.sendmail.call_count == 5
```

- [ ] **Step 6: Run all email service tests**

```bash
cd backend
pytest tests/test_email_service.py -v
```

Expected output: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/email_service.py backend/tests/test_email_service.py
git commit -m "feat: add EmailService with SMTP + retry logic

- Implement EmailService class with Gmail SMTP configuration
- Add exponential backoff retry logic (5 attempts)
- Mount HTML email with intimação data (arquivo, confianca, tipo_pericia, setor, riscos, campos)
- Comprehensive logging for debugging
- Unit tests for success, retry, and critical failure paths
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Integrate EmailService into IntimacaoService

**Files:**
- Modify: `backend/app/services/intimacao_service.py` (or equivalent processing endpoint)
- Test: `backend/tests/test_intimacao_with_email.py`

**Interfaces:**
- Consumes: `EmailService.enviar_notificacao(usuario_id: int, analise: dict) -> bool`
- Produces: IntimacaoService calls EmailService after successful processing (non-blocking)

[... rest of tasks 2-7 ...]
