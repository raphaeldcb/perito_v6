"""
Task 3: AI Feedback Classification Service

Classifies user feedback by severity and scope using Qwen 3.6 (Ollama local).
Returns: severity (LOW|MEDIUM|HIGH|CRITICAL), is_in_scope (bool), summary (str)

Implements direct Ollama HTTP API (no external CLI dependencies).
Timeout: 30 seconds. Fallback: MEDIUM/in-scope/truncated summary on error.
"""

import logging
import json
from typing import Dict
import requests

from app.config.settings import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """Analise este feedback de usuário e classifique:

FEEDBACK:
{description}

TAREFA:
1. Determinar SEVERIDADE: LOW, MEDIUM, HIGH, CRITICAL
2. Determinar SCOPE: é um bug/feature do Perito v6 (in_scope=true) ou fora do escopo?
3. Resumir em 1-2 linhas

RESPONDA EM JSON:
{{
  "severity": "HIGH",
  "is_in_scope": true,
  "summary": "Bug: login falha com erro 500 quando usuário clica botão"
}}
"""


def analyze_feedback(description: str, attachment_path: str = None) -> Dict:
    """
    Analyze user feedback using Qwen 3.6 (Ollama local) to classify severity and scope.

    Args:
        description: User feedback text to analyze
        attachment_path: Optional path to attachment file (for future use)

    Returns:
        Dict with keys:
            - severity: str (LOW|MEDIUM|HIGH|CRITICAL)
            - is_in_scope: bool (true if bug/feature of Perito v6, false if out-of-scope)
            - summary: str (1-2 line summary of the feedback)

    Fallback on error: returns {"severity": "MEDIUM", "is_in_scope": True, "summary": description[:100]}
    """

    prompt = CLASSIFICATION_PROMPT.format(description=description)

    try:
        # Call Ollama HTTP API directly (no external CLI dependency)
        resp = requests.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": "qwen3:14b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        if resp.status_code != 200:
            logger.warning(f"Ollama API error: {resp.status_code} - {resp.text}")
            return _fallback_analysis(description)

        response_text = resp.json().get("response", "")

        # Parse JSON from response (extract JSON object from potential text)
        start = response_text.find('{')
        end = response_text.rfind('}') + 1

        if start >= 0 and end > start:
            json_str = response_text[start:end]
            analysis = json.loads(json_str)

            # Validate response structure
            if _validate_analysis(analysis):
                logger.info(f"Feedback analysis: {analysis}")
                return analysis
            else:
                logger.warning(f"Invalid analysis structure: {analysis}")
                return _fallback_analysis(description)
        else:
            logger.warning("No JSON found in Ollama response")
            return _fallback_analysis(description)

    except requests.exceptions.Timeout:
        logger.error("Ollama request timeout (30 seconds)")
        return _fallback_analysis(description)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return _fallback_analysis(description)

    except Exception as e:
        logger.error(f"Feedback analysis error: {e}", exc_info=True)
        return _fallback_analysis(description)


def _validate_analysis(analysis: Dict) -> bool:
    """
    Validate that analysis dict has required fields with valid values.

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(analysis, dict):
        return False

    # Check required keys
    if "severity" not in analysis or "is_in_scope" not in analysis or "summary" not in analysis:
        return False

    # Validate severity
    if analysis["severity"] not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        return False

    # Validate is_in_scope is boolean
    if not isinstance(analysis["is_in_scope"], bool):
        return False

    # Validate summary is string
    if not isinstance(analysis["summary"], str):
        return False

    return True


def _fallback_analysis(description: str) -> Dict:
    """
    Return safe fallback analysis when Ollama is unavailable or error occurs.

    Fallback: MEDIUM severity, in-scope, truncated description
    """
    return {
        "severity": "MEDIUM",
        "is_in_scope": True,
        "summary": description[:100]
    }
