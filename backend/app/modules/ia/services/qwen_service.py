"""
Qwen LLM service for IA module.

Handles analysis requests via Ollama (primary) or Claude API (fallback).
Includes token counting and cost tracking.
"""

import logging
import os
import httpx
from typing import Optional, Dict, Any
import json

from app.config import settings
from app.shared.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

# LLM configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "perito-qwen")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# Timeouts
OLLAMA_TIMEOUT = 30  # seconds
CLAUDE_TIMEOUT = 30  # seconds


class QwenService:
    """
    LLM service for Qwen analysis.

    Primary: Ollama local (perito-qwen)
    Fallback: Claude API (if available)
    """

    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
        self.qwen_api_key = QWEN_API_KEY
        self.timeout = OLLAMA_TIMEOUT

    async def analyze(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze text using Qwen.

        Args:
            text: Text to analyze (up to 50k chars)
            system_prompt: Optional system prompt override
            context: Additional context (user metadata, processo info, etc)

        Returns:
            {
                "response": str,  # Analysis result
                "model": str,  # Which model was used
                "provider": str,  # ollama or claude
                "input_tokens": int,
                "output_tokens": int,
                "cost_usd": float,  # Only for Claude API
            }
        """
        # Prepare system prompt
        if not system_prompt:
            system_prompt = self._get_system_prompt()

        # Try Ollama first
        try:
            result = await self._call_ollama(text, system_prompt)
            logger.info(f"✅ Ollama analysis completed: {result['output_tokens']} tokens")
            return result
        except Exception as e:
            logger.warning(f"⚠️ Ollama failed: {e}")

        # Fallback to Claude API if configured
        if self.qwen_api_key:
            try:
                result = await self._call_claude_api(text, system_prompt)
                logger.info(f"✅ Claude API analysis completed: {result['output_tokens']} tokens")
                return result
            except Exception as e:
                logger.error(f"❌ Claude API also failed: {e}")
                raise

        raise ExternalServiceException(
            detail="Ollama unavailable and Claude API not configured",
            error_code="LLM_UNAVAILABLE",
        )

    async def _call_ollama(
        self,
        text: str,
        system_prompt: str,
    ) -> Dict[str, Any]:
        """Call Ollama API."""
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # Extract response
                message_content = data.get("message", {}).get("content", "")
                if not message_content:
                    raise ValueError("Empty response from Ollama")

                # Token counting (Ollama doesn't always return these)
                input_tokens = data.get("prompt_eval_count", len(text.split()))
                output_tokens = data.get("eval_count", len(message_content.split()))

                return {
                    "response": message_content,
                    "model": self.ollama_model,
                    "provider": "ollama",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": 0.0,  # Local, no cost
                }
            except httpx.ConnectError as e:
                raise ExternalServiceException(
                    detail=f"Cannot connect to Ollama at {self.ollama_url}",
                    error_code="OLLAMA_CONNECTION_ERROR",
                ) from e
            except Exception as e:
                raise ExternalServiceException(
                    detail=f"Ollama API error: {str(e)}",
                    error_code="OLLAMA_ERROR",
                ) from e

    async def _call_claude_api(
        self,
        text: str,
        system_prompt: str,
    ) -> Dict[str, Any]:
        """Call Claude API via DashScope or direct Anthropic."""
        # TODO: Implement Claude API integration when needed
        # For now, just return a placeholder error
        raise NotImplementedError("Claude API integration not yet implemented")

    def _get_system_prompt(self) -> str:
        """Get default system prompt for Qwen."""
        return """Você é um assistente jurídico especializado em perícia judicial.

Sua tarefa é:
1. Analisar textos jurídicos com precisão técnica
2. Explicar conceitos legais de forma clara
3. Identificar questões principais e secundárias
4. Fundamentar conclusões em lei e jurisprudência
5. Ser honesto sobre limitações — nunca inventar lei ou precedente

Responda sempre em português, de forma estruturada, com clareza técnica."""


# Singleton instance
_qwen_service: Optional[QwenService] = None


def get_qwen_service() -> QwenService:
    """Get or create QwenService singleton."""
    global _qwen_service
    if _qwen_service is None:
        _qwen_service = QwenService()
    return _qwen_service
