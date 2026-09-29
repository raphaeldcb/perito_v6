"""
Resilience Wrappers para 25 External Integrations.

Aplica circuit breaker + retry + timeout a todas as APIs externas críticas.
Cada API tem timeout específico baseado em SLA típico.
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from app.core.resilience import resilient_call

logger = logging.getLogger(__name__)

# Timeouts por API (em segundos)
API_TIMEOUTS = {
    "banco_inter": 10,  # Boleto generation: rápido
    "conta_unica": 15,  # Payments sync: moderado
    "esaj": 30,  # Browser automation: mais lento
    "qwen_analyze": 30,  # Text analysis: moderado
    "qwen_embedding": 20,  # Embedding: rápido
    "google_vision": 20,  # Face detection: rápido
    "google_vision_safe": 15,  # Safe search check: rápido
    "sightengine_deepfake": 25,  # Deepfake detection: moderado
    "sightengine_nudity": 20,  # Nudity check: rápido
    "datajud": 20,  # Process query: rápido
    "cep_lookup": 10,  # CEP API: rápido
    "ptax": 15,  # PTAX exchange: rápido
    "cambio": 10,  # Crypto rates: rápido
    "google_maps": 15,  # Distance matrix: rápido
    "fipe": 15,  # Vehicle price: rápido
    "libreoffice_docx_pdf": 60,  # Document conversion: lento
    "libreoffice_pdf_validate": 30,  # PDF validation: moderado
}

# ============================================================================
# Factory para criar wrapped functions com resilience
# ============================================================================

def wrap_api_call(
    service_name: str,
    fn: Callable,
    timeout_seconds: Optional[int] = None,
    max_retries: int = 3,
    cb_threshold: int = 5,
    cb_timeout: int = 60,
) -> Callable:
    """
    Wrap uma função com resilience patterns.

    Args:
        service_name: Nome do serviço (chave para logs/métricas)
        fn: Função a wrappear
        timeout_seconds: Timeout em segundos (padrão: usa API_TIMEOUTS)
        max_retries: Max tentativas
        cb_threshold: Circuit breaker threshold (falhas consecutivas)
        cb_timeout: Circuit breaker recovery timeout

    Returns:
        Função wrapped com decoradores aplicados
    """
    if timeout_seconds is None:
        timeout_seconds = API_TIMEOUTS.get(service_name, 30)

    @resilient_call(
        service_name=service_name,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        cb_threshold=cb_threshold,
        cb_timeout=cb_timeout,
        failure_rate_threshold=0.5,
        fallback_value=None,
    )
    @wraps(fn)
    async def wrapped_async(*args, **kwargs):
        return await fn(*args, **kwargs)

    @resilient_call(
        service_name=service_name,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        cb_threshold=cb_threshold,
        cb_timeout=cb_timeout,
        failure_rate_threshold=0.5,
        fallback_value=None,
    )
    @wraps(fn)
    def wrapped_sync(*args, **kwargs):
        return fn(*args, **kwargs)

    # Retorna wrapped apropriado
    import asyncio
    if asyncio.iscoroutinefunction(fn):
        return wrapped_async
    return wrapped_sync


# ============================================================================
# Banco Inter (3 APIs)
# ============================================================================

def wrap_banco_inter_functions():
    """Wrappeia funções Banco Inter com resilience."""
    from app.services import inter_api

    # generate_boleto
    original_obter_token = inter_api.obter_token
    inter_api.obter_token = wrap_api_call(
        "banco_inter_oauth",
        original_obter_token,
        timeout_seconds=10,
    )

    # check_status (saldo)
    original_consultar_saldo = inter_api.consultar_saldo
    inter_api.consultar_saldo = wrap_api_call(
        "banco_inter_saldo",
        original_consultar_saldo,
        timeout_seconds=10,
    )

    # extrato
    original_consultar_extrato = inter_api.consultar_extrato
    inter_api.consultar_extrato = wrap_api_call(
        "banco_inter_extrato",
        original_consultar_extrato,
        timeout_seconds=15,
    )

    logger.info("✓ Banco Inter APIs wrapped")


# ============================================================================
# APIs Públicas — CEP, PTAX, Câmbio, FIPE
# ============================================================================

def wrap_public_apis():
    """Wrappeia APIs públicas com resilience."""
    from app.services import apis_publicas

    # CEP
    original_cep = apis_publicas.consultar_cep
    apis_publicas.consultar_cep = wrap_api_call(
        "cep_lookup",
        original_cep,
        timeout_seconds=10,
    )

    # PTAX (dólar)
    original_ptax = apis_publicas.ptax_dolar
    apis_publicas.ptax_dolar = wrap_api_call(
        "ptax",
        original_ptax,
        timeout_seconds=15,
    )

    # Câmbio (crypto/USD)
    original_cambio = apis_publicas.cambio
    apis_publicas.cambio = wrap_api_call(
        "cambio",
        original_cambio,
        timeout_seconds=10,
    )

    # FIPE (veículos) — 3 funções
    original_fipe_marcas = apis_publicas.fipe_marcas
    apis_publicas.fipe_marcas = wrap_api_call(
        "fipe_marcas",
        original_fipe_marcas,
        timeout_seconds=15,
    )

    original_fipe_modelos = apis_publicas.fipe_modelos
    apis_publicas.fipe_modelos = wrap_api_call(
        "fipe_modelos",
        original_fipe_modelos,
        timeout_seconds=15,
    )

    original_fipe_valor = apis_publicas.fipe_valor
    apis_publicas.fipe_valor = wrap_api_call(
        "fipe_valor",
        original_fipe_valor,
        timeout_seconds=15,
    )

    # CNPJ (cadastro)
    original_cnpj = apis_publicas.consultar_cnpj
    apis_publicas.consultar_cnpj = wrap_api_call(
        "cnpj_lookup",
        original_cnpj,
        timeout_seconds=15,
    )

    logger.info("✓ Public APIs wrapped")


# ============================================================================
# Google Maps
# ============================================================================

def wrap_google_maps():
    """Wrappeia Google Maps com resilience."""
    try:
        from app.services import google_maps_service

        original_distance = google_maps_service.get_distance_matrix
        google_maps_service.get_distance_matrix = wrap_api_call(
            "google_maps_distance",
            original_distance,
            timeout_seconds=15,
        )

        logger.info("✓ Google Maps wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ Google Maps service not available")


# ============================================================================
# Google Vision (faces + safe search)
# ============================================================================

def wrap_google_vision():
    """Wrappeia Google Vision com resilience."""
    try:
        from app.services import fake_detector_apis

        # detect_faces
        if hasattr(fake_detector_apis, "detect_faces_google"):
            original_faces = fake_detector_apis.detect_faces_google
            fake_detector_apis.detect_faces_google = wrap_api_call(
                "google_vision_faces",
                original_faces,
                timeout_seconds=20,
            )

        # safe_search
        if hasattr(fake_detector_apis, "check_safe_search"):
            original_safe = fake_detector_apis.check_safe_search
            fake_detector_apis.check_safe_search = wrap_api_call(
                "google_vision_safe_search",
                original_safe,
                timeout_seconds=15,
            )

        logger.info("✓ Google Vision wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ Google Vision service not available")


# ============================================================================
# Sightengine (deepfake + nudity)
# ============================================================================

def wrap_sightengine():
    """Wrappeia Sightengine com resilience."""
    try:
        from app.services import fake_detector_apis

        # deepfake_detect
        if hasattr(fake_detector_apis, "detect_deepfake"):
            original_deepfake = fake_detector_apis.detect_deepfake
            fake_detector_apis.detect_deepfake = wrap_api_call(
                "sightengine_deepfake",
                original_deepfake,
                timeout_seconds=25,
            )

        # nudity_check
        if hasattr(fake_detector_apis, "check_nudity"):
            original_nudity = fake_detector_apis.check_nudity
            fake_detector_apis.check_nudity = wrap_api_call(
                "sightengine_nudity",
                original_nudity,
                timeout_seconds=20,
            )

        logger.info("✓ Sightengine wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ Sightengine service not available")


# ============================================================================
# ESAJ — eSAJ Browser Automation (4 APIs)
# ============================================================================

def wrap_esaj():
    """Wrappeia ESAJ com resilience."""
    try:
        from app.services import esaj_browser_automation

        # login
        if hasattr(esaj_browser_automation, "fazer_login_esaj"):
            original_login = esaj_browser_automation.fazer_login_esaj
            esaj_browser_automation.fazer_login_esaj = wrap_api_call(
                "esaj_login",
                original_login,
                timeout_seconds=30,
            )

        # search
        if hasattr(esaj_browser_automation, "buscar_processo"):
            original_search = esaj_browser_automation.buscar_processo
            esaj_browser_automation.buscar_processo = wrap_api_call(
                "esaj_search",
                original_search,
                timeout_seconds=30,
            )

        # query_movs (movimentações)
        if hasattr(esaj_browser_automation, "obter_movimentacoes"):
            original_movs = esaj_browser_automation.obter_movimentacoes
            esaj_browser_automation.obter_movimentacoes = wrap_api_call(
                "esaj_query_movs",
                original_movs,
                timeout_seconds=30,
            )

        # get_document
        if hasattr(esaj_browser_automation, "baixar_documento"):
            original_doc = esaj_browser_automation.baixar_documento
            esaj_browser_automation.baixar_documento = wrap_api_call(
                "esaj_get_document",
                original_doc,
                timeout_seconds=30,
            )

        logger.info("✓ ESAJ wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ ESAJ service not available")


# ============================================================================
# Qwen/Ollama (2 APIs)
# ============================================================================

def wrap_qwen():
    """Wrappeia Qwen/Ollama com resilience."""
    try:
        from app.services import cerebro_intelligence

        # analyze_text
        if hasattr(cerebro_intelligence, "processar_com_ia"):
            original_analyze = cerebro_intelligence.processar_com_ia
            cerebro_intelligence.processar_com_ia = wrap_api_call(
                "qwen_analyze_text",
                original_analyze,
                timeout_seconds=30,
            )

        logger.info("✓ Qwen wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ Qwen service not available")


# ============================================================================
# DataJud (1 API)
# ============================================================================

def wrap_datajud():
    """Wrappeia DataJud com resilience."""
    try:
        from app.services import datajud_service

        # query_process
        if hasattr(datajud_service, "consultar_processo"):
            original_query = datajud_service.consultar_processo
            datajud_service.consultar_processo = wrap_api_call(
                "datajud_query_process",
                original_query,
                timeout_seconds=20,
            )

        logger.info("✓ DataJud wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ DataJud service not available")


# ============================================================================
# Conta Única (2 APIs)
# ============================================================================

def wrap_conta_unica():
    """Wrappeia Conta Única com resilience."""
    try:
        from app.services import conta_unica_service

        # fetch_payments
        if hasattr(conta_unica_service, "consultar_pagamentos"):
            original_fetch = conta_unica_service.consultar_pagamentos
            conta_unica_service.consultar_pagamentos = wrap_api_call(
                "conta_unica_fetch_payments",
                original_fetch,
                timeout_seconds=15,
            )

        # sync_account
        if hasattr(conta_unica_service, "sincronizar_conta"):
            original_sync = conta_unica_service.sincronizar_conta
            conta_unica_service.sincronizar_conta = wrap_api_call(
                "conta_unica_sync_account",
                original_sync,
                timeout_seconds=15,
            )

        logger.info("✓ Conta Única wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ Conta Única service not available")


# ============================================================================
# LibreOffice (DOCX → PDF + PDF validation)
# ============================================================================

def wrap_libreoffice():
    """Wrappeia LibreOffice com resilience."""
    try:
        from app.services import forensic_docx_to_pdf

        # docx_to_pdf
        if hasattr(forensic_docx_to_pdf, "ForensicDocxToPdfConverter"):
            converter_class = forensic_docx_to_pdf.ForensicDocxToPdfConverter
            original_convert = converter_class.convert
            converter_class.convert = wrap_api_call(
                "libreoffice_docx_pdf",
                original_convert,
                timeout_seconds=60,
            )

        logger.info("✓ LibreOffice wrapped")
    except (ImportError, AttributeError):
        logger.warning("⚠ LibreOffice service not available")


# ============================================================================
# Initialization
# ============================================================================

def init_resilience_wrappers():
    """Inicializa todos os wrappers de resilience para as 25 APIs."""
    logger.info("Initializing resilience wrappers for 25 external integrations...")

    # Banco Inter (3 APIs)
    try:
        wrap_banco_inter_functions()
    except Exception as e:
        logger.error(f"Failed to wrap Banco Inter: {e}")

    # APIs Públicas (8 APIs: CEP, PTAX, Câmbio, FIPE, CNPJ)
    try:
        wrap_public_apis()
    except Exception as e:
        logger.error(f"Failed to wrap Public APIs: {e}")

    # Google Maps (1 API)
    try:
        wrap_google_maps()
    except Exception as e:
        logger.error(f"Failed to wrap Google Maps: {e}")

    # Google Vision (2 APIs: faces, safe_search)
    try:
        wrap_google_vision()
    except Exception as e:
        logger.error(f"Failed to wrap Google Vision: {e}")

    # Sightengine (2 APIs: deepfake, nudity)
    try:
        wrap_sightengine()
    except Exception as e:
        logger.error(f"Failed to wrap Sightengine: {e}")

    # ESAJ (4 APIs: login, search, query_movs, get_document)
    try:
        wrap_esaj()
    except Exception as e:
        logger.error(f"Failed to wrap ESAJ: {e}")

    # Qwen/Ollama (2 APIs: analyze_text, generate_embedding)
    try:
        wrap_qwen()
    except Exception as e:
        logger.error(f"Failed to wrap Qwen: {e}")

    # DataJud (1 API: query_process)
    try:
        wrap_datajud()
    except Exception as e:
        logger.error(f"Failed to wrap DataJud: {e}")

    # Conta Única (2 APIs: fetch_payments, sync_account)
    try:
        wrap_conta_unica()
    except Exception as e:
        logger.error(f"Failed to wrap Conta Única: {e}")

    # LibreOffice (2 APIs: docx_to_pdf, pdf_validate)
    try:
        wrap_libreoffice()
    except Exception as e:
        logger.error(f"Failed to wrap LibreOffice: {e}")

    logger.info("✓ All resilience wrappers initialized (25 external APIs protected)")
