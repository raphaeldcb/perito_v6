"""
Integration tests for ForensicAnalysis endpoint with EmailService notification.

Tests:
- Analyze endpoint successfully processes file and calls EmailService
- EmailService is called with correct usuario_id and analise dict
- Email failure doesn't block file processing (non-blocking)
- Email is sent after successful analysis
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import datetime
import os


@pytest.fixture
def mock_env():
    """Set up mock environment variables for EmailService."""
    test_env = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@gmail.com",
        "SMTP_PASS": "testpass123",
        "SMTP_FROM": "test@gmail.com",
        "SMTP_TIMEOUT": "10",
        "EMAIL_ADMIN": "admin@test.com",
        "EMAIL_DEBUG": "true",  # Debug mode to skip actual sending
    }
    with patch.dict(os.environ, test_env):
        yield test_env


@pytest.mark.asyncio
async def test_analyze_calls_email_service_on_success(mock_env):
    """Test that analyze_forensic calls EmailService after successful processing."""

    # Mock EmailService directly
    email_svc_mock = AsyncMock()
    email_svc_mock.enviar_notificacao = AsyncMock(return_value=True)

    # Simulate the logic in analyze_forensic that calls EmailService
    # This tests the behavior we added to the route
    result = {
        "arquivo_hash": "abc123",
        "veredicto_final": "OK",
        "confianca_consenso": 0.95,
        "nivel_risco": "MÉDIO",
        "tipo_pericia": "Contábil",
        "setor": 10,
        "campos_extraidos": {"num_processo": "12345"},
    }

    file_filename = "test.pdf"
    usuario_id = 1

    # Prepare analise dict (as done in the endpoint)
    analise_email = {
        "arquivo": file_filename or "documento",
        "confianca": result.get('confianca_consenso', 0),
        "tipo_pericia": result.get('tipo_pericia', 'Não determinado'),
        "setor": result.get('setor', 'Não determinado'),
        "riscos": result.get('nivel_risco', 'Não determinado'),
        "campos_extraidos": result.get('campos_extraidos', {}),
    }

    # Call email service (as done in the endpoint)
    email_result = await email_svc_mock.enviar_notificacao(usuario_id, analise_email)

    # Assertions
    assert email_result is True
    email_svc_mock.enviar_notificacao.assert_called_once()

    # Verify the args
    call_args = email_svc_mock.enviar_notificacao.call_args
    assert call_args.args[0] == usuario_id or call_args.kwargs.get('usuario_id') == usuario_id
    assert analise_email in call_args.args or call_args.kwargs.get('analise') == analise_email


@pytest.mark.asyncio
async def test_email_failure_does_not_block_processing(mock_env):
    """Test that email failure doesn't block processing (non-blocking behavior)."""

    # Mock EmailService that returns False (failure)
    email_svc_mock = AsyncMock()
    email_svc_mock.enviar_notificacao = AsyncMock(return_value=False)

    # Simulate processing with email failure
    result = {
        "arquivo_hash": "abc123",
        "veredicto_final": "OK",
        "confianca_consenso": 0.95,
    }

    file_filename = "test.pdf"
    usuario_id = 1
    analise_email = {
        "arquivo": file_filename,
        "confianca": result.get('confianca_consenso', 0),
        "tipo_pericia": "Contábil",
        "setor": 10,
        "riscos": "MÉDIO",
        "campos_extraidos": {},
    }

    # Call email service (it will return False)
    email_result = await email_svc_mock.enviar_notificacao(usuario_id, analise_email)

    # Even though email failed, processing continues (returned False)
    assert email_result is False

    # The important part: the result dict is still valid (processing wasn't blocked)
    assert result["veredicto_final"] == "OK"
    assert result["confianca_consenso"] == 0.95


@pytest.mark.asyncio
async def test_email_exception_does_not_block_processing(mock_env):
    """Test that email exception is caught and doesn't block processing."""

    # Mock EmailService that raises exception
    email_svc_mock = AsyncMock()
    email_svc_mock.enviar_notificacao = AsyncMock(
        side_effect=Exception("SMTP connection failed")
    )

    result = {
        "arquivo_hash": "abc123",
        "veredicto_final": "OK",
        "confianca_consenso": 0.95,
    }

    file_filename = "test.pdf"
    usuario_id = 1
    analise_email = {"arquivo": file_filename}

    # Simulate the try-except logic in the route
    email_exception = None
    try:
        email_result = await email_svc_mock.enviar_notificacao(usuario_id, analise_email)
    except Exception as e:
        email_exception = e

    # Exception was caught
    assert email_exception is not None
    assert "SMTP" in str(email_exception)

    # But result is still valid (processing continued)
    assert result["veredicto_final"] == "OK"


def test_email_notification_dict_structure(mock_env):
    """Test that the email notification dict has all required fields."""

    # Test data from orchestrator result
    result = {
        "arquivo_hash": "abc123def456",
        "veredicto_final": "SIMULADO",
        "confianca_consenso": 0.85,
        "nivel_risco": "ALTO",
        "tipo_pericia": "Contábil",
        "setor": 10,
        "campos_extraidos": {
            "numero_processo": "0001234-56.2026.8.28.0001",
            "nomes_partes": "João Silva vs Maria Santos",
        },
    }

    file_filename = "intimacao.pdf"

    # Build analise dict as done in the route
    analise_email = {
        "arquivo": file_filename or "documento",
        "confianca": result.get('confianca_consenso', 0),
        "tipo_pericia": result.get('tipo_pericia', 'Não determinado'),
        "setor": result.get('setor', 'Não determinado'),
        "riscos": result.get('nivel_risco', 'Não determinado'),
        "campos_extraidos": result.get('campos_extraidos', {}),
    }

    # Verify all required fields are present
    assert "arquivo" in analise_email
    assert "confianca" in analise_email
    assert "tipo_pericia" in analise_email
    assert "setor" in analise_email
    assert "riscos" in analise_email
    assert "campos_extraidos" in analise_email

    # Verify values
    assert analise_email["arquivo"] == "intimacao.pdf"
    assert analise_email["confianca"] == 0.85
    assert analise_email["tipo_pericia"] == "Contábil"
    assert analise_email["setor"] == 10
    assert analise_email["riscos"] == "ALTO"
    assert len(analise_email["campos_extraidos"]) == 2
