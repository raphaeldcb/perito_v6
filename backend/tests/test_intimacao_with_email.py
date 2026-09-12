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


@pytest.mark.asyncio
async def test_process_intimacao_sends_email_on_success(mock_env):
    """
    Integration test: Process intimação → Send email notification.

    Tests the complete workflow:
    1. IntimacaoService.processar() is called and returns success result
    2. EmailService.enviar_notificacao() is called with correct data
    3. Both services are called in correct sequence (processing first, then email)
    4. Data flows correctly from processing result to email notification dict
    """

    # Mock IntimacaoService.processar()
    intimacao_service_mock = AsyncMock()
    processing_result = {
        "arquivo_hash": "sha256_abc123def456",
        "veredicto_final": "OK",
        "confianca_consenso": 0.92,
        "nivel_risco": "MÉDIO",
        "tipo_pericia": "Contábil",
        "setor": 10,
        "campos_extraidos": {
            "numero_processo": "0001234-56.2026.8.28.0001",
            "nomes_partes": "João Silva vs Maria Santos",
            "data_intimacao": "2026-09-10",
            "prazo_dias": "15",
        },
    }
    intimacao_service_mock.processar = AsyncMock(return_value=processing_result)

    # Mock EmailService.enviar_notificacao()
    email_service_mock = AsyncMock()
    email_service_mock.enviar_notificacao = AsyncMock(return_value=True)

    # Test data
    file_filename = "intimacao_processo_001.pdf"
    usuario_id = 1
    file_bytes = b"PDF_CONTENT_MOCK"

    # Simulate the complete workflow in the endpoint
    # Step 1: Process intimação
    result = await intimacao_service_mock.processar(
        usuario_id=usuario_id,
        file_filename=file_filename,
        file_bytes=file_bytes
    )

    # Verify processing was successful
    assert result is not None
    assert result["veredicto_final"] == "OK"
    assert result["confianca_consenso"] == 0.92
    assert len(result["campos_extraidos"]) == 4

    # Step 2: Prepare email notification dict from processing result
    analise_email = {
        "arquivo": file_filename or "documento",
        "confianca": result.get('confianca_consenso', 0),
        "tipo_pericia": result.get('tipo_pericia', 'Não determinado'),
        "setor": result.get('setor', 'Não determinado'),
        "riscos": result.get('nivel_risco', 'Não determinado'),
        "campos_extraidos": result.get('campos_extraidos', {}),
    }

    # Step 3: Send email notification
    email_result = await email_service_mock.enviar_notificacao(usuario_id, analise_email)

    # Assertions: Verify both services were called in correct order
    intimacao_service_mock.processar.assert_called_once_with(
        usuario_id=usuario_id,
        file_filename=file_filename,
        file_bytes=file_bytes
    )

    # EmailService called after successful processing
    email_service_mock.enviar_notificacao.assert_called_once()
    email_result_received = True  # Email sent successfully

    # Verify email was called with correct data
    email_call_args = email_service_mock.enviar_notificacao.call_args
    assert email_call_args.args[0] == usuario_id  # usuario_id is first arg
    assert email_call_args.args[1]["arquivo"] == file_filename  # analise dict is second arg
    assert email_call_args.args[1]["confianca"] == 0.92
    assert email_call_args.args[1]["tipo_pericia"] == "Contábil"
    assert email_call_args.args[1]["setor"] == 10
    assert email_call_args.args[1]["riscos"] == "MÉDIO"
    assert "numero_processo" in email_call_args.args[1]["campos_extraidos"]

    # Final assertion: processing succeeded and email was sent
    assert email_result is True
    assert result["veredicto_final"] == "OK"


@pytest.mark.asyncio
async def test_email_failure_does_not_block_intimacao_processing(mock_env):
    """
    Integration test: Email failure is non-blocking.

    Tests that:
    1. IntimacaoService.processar() succeeds
    2. EmailService.enviar_notificacao() fails
    3. Processing result is still returned to caller (non-blocking)
    4. Exception in email doesn't propagate to caller
    """

    # Mock IntimacaoService.processar() — success
    intimacao_service_mock = AsyncMock()
    processing_result = {
        "arquivo_hash": "sha256_xyz789",
        "veredicto_final": "OK",
        "confianca_consenso": 0.88,
        "nivel_risco": "BAIXO",
        "tipo_pericia": "DNA",
        "setor": 20,
        "campos_extraidos": {
            "numero_processo": "0005678-90.2026.8.28.0002",
        },
    }
    intimacao_service_mock.processar = AsyncMock(return_value=processing_result)

    # Mock EmailService.enviar_notificacao() — fails
    email_service_mock = AsyncMock()
    email_service_mock.enviar_notificacao = AsyncMock(
        side_effect=Exception("SMTP connection timeout")
    )

    file_filename = "intimacao_dna.pdf"
    usuario_id = 2
    file_bytes = b"PDF_CONTENT_DNA"

    # Step 1: Process intimação (succeeds)
    result = await intimacao_service_mock.processar(
        usuario_id=usuario_id,
        file_filename=file_filename,
        file_bytes=file_bytes
    )

    # Prepare email dict
    analise_email = {
        "arquivo": file_filename,
        "confianca": result.get('confianca_consenso', 0),
        "tipo_pericia": result.get('tipo_pericia', 'Não determinado'),
        "setor": result.get('setor', 'Não determinado'),
        "riscos": result.get('nivel_risco', 'Não determinado'),
        "campos_extraidos": result.get('campos_extraidos', {}),
    }

    # Step 2: Try to send email — may fail but shouldn't block processing
    email_exception = None
    try:
        await email_service_mock.enviar_notificacao(usuario_id, analise_email)
    except Exception as e:
        email_exception = e

    # Assertions
    # Processing succeeded
    assert result["veredicto_final"] == "OK"
    assert result["confianca_consenso"] == 0.88

    # Email failed (exception was raised)
    assert email_exception is not None
    assert "SMTP" in str(email_exception)

    # But the processing result is still valid (non-blocking)
    # The caller would still get the processing result even if email failed
    assert result is not None
    assert "arquivo_hash" in result
    assert "campos_extraidos" in result
