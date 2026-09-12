"""
Unit tests for EmailService — Email notification with retry logic.

Tests:
- Send email successfully on first attempt
- Retry after transient failure
- Critical failure after 5 retries
- Admin notification on critical failure
- Exponential backoff timing
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import datetime
import os


@pytest.fixture
def mock_env():
    """Set up mock environment variables."""
    test_env = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@gmail.com",
        "SMTP_PASS": "testpass123",
        "SMTP_FROM": "test@gmail.com",
        "SMTP_TIMEOUT": "10",
        "EMAIL_ADMIN": "admin@test.com",
        "EMAIL_DEBUG": "false",
    }
    with patch.dict(os.environ, test_env):
        yield test_env


@pytest.fixture
def sample_analise():
    """Sample intimação analysis data."""
    return {
        "arquivo": "intimacao_001.pdf",
        "confianca": 95,
        "tipo_pericia": "Contábil",
        "setor": 10,
        "riscos": "Médio",
        "campos_extraidos": {
            "numero_processo": "0001234-56.2026.8.28.0001",
            "nomes_partes": "João Silva vs Maria Santos",
            "data_distribuicao": "2026-09-01",
        },
    }


def test_email_service_sends_successfully_on_first_attempt(mock_env, sample_analise):
    """Email sends successfully on first attempt."""
    from app.services.email_service import EmailService

    service = EmailService()

    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=None)

        result = asyncio.run(
            service.enviar_notificacao(usuario_id=1, analise=sample_analise)
        )

    assert result is True
    mock_smtp_class.assert_called_once()
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once()
    mock_smtp.send_message.assert_called_once()


def test_email_service_retries_on_transient_failure(mock_env, sample_analise):
    """Retry logic works: fails once, succeeds on second attempt."""
    import smtplib
    from app.services.email_service import EmailService

    service = EmailService()

    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_class:
        mock_smtp = MagicMock()
        # First call fails with transient error, second succeeds
        mock_smtp.send_message.side_effect = [
            smtplib.SMTPException("Temp error"),
            None,
        ]
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=None)

        with patch("app.services.email_service.asyncio.sleep", new_callable=AsyncMock):
            result = asyncio.run(
                service.enviar_notificacao(usuario_id=1, analise=sample_analise)
            )

    assert result is True
    # Should be called twice (retry on failure)
    assert mock_smtp.send_message.call_count == 2


def test_email_service_returns_false_after_max_retries(mock_env, sample_analise):
    """After 5 failures, return False."""
    import smtplib
    from app.services.email_service import EmailService

    service = EmailService()

    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_class:
        mock_smtp = MagicMock()
        # All attempts fail with transient error
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Transient error")
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=None)

        with patch("app.services.email_service.asyncio.sleep", new_callable=AsyncMock):
            with patch.object(
                service, "_notify_admin_critical", new_callable=AsyncMock
            ):
                result = asyncio.run(
                    service.enviar_notificacao(usuario_id=1, analise=sample_analise)
                )

    assert result is False
    # Should be called 5 times (max retries)
    assert mock_smtp.send_message.call_count == 5


def test_email_html_contains_analysis_data(mock_env, sample_analise):
    """HTML email contains all required analysis data."""
    from app.services.email_service import EmailService

    service = EmailService()

    # Mount HTML directly
    html = service._mount_html_email(sample_analise)

    assert "intimacao_001.pdf" in html
    assert "95" in html
    assert "Contábil" in html
    assert "Médio" in html
    assert "numero_processo" in html
    assert "0001234-56.2026.8.28.0001" in html


def test_email_service_logs_success(mock_env, sample_analise, caplog):
    """Log info message on success."""
    import logging
    from app.services.email_service import EmailService

    service = EmailService()

    with caplog.at_level(logging.INFO, logger="app.services.email_service"):
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value = mock_smtp
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=None)

            asyncio.run(service.enviar_notificacao(usuario_id=1, analise=sample_analise))

    assert any("Email enviado" in record.message for record in caplog.records)


def test_email_service_logs_error_on_max_retries(mock_env, sample_analise, caplog):
    """Log error message after max retries."""
    import logging
    import smtplib
    from app.services.email_service import EmailService

    service = EmailService()

    with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp.send_message.side_effect = smtplib.SMTPException("Error")
            mock_smtp_class.return_value = mock_smtp
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=None)

            with patch("app.services.email_service.asyncio.sleep", new_callable=AsyncMock):
                with patch.object(
                    service, "_notify_admin_critical", new_callable=AsyncMock
                ):
                    asyncio.run(
                        service.enviar_notificacao(usuario_id=1, analise=sample_analise)
                    )

    assert any("falhou após" in record.message for record in caplog.records)


def test_email_subject_is_descriptive(mock_env, sample_analise):
    """Email subject contains action and file name."""
    from app.services.email_service import EmailService

    service = EmailService()

    subject = service._mount_email_subject(sample_analise)

    assert "Intimação Processada" in subject or "intimacao" in subject.lower()
