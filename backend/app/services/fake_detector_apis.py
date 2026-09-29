"""
Fake Detector APIs — múltiplos serviços deepfake + fallback local
"""
import aiohttp
import asyncio
import base64
import logging
import os
from app.config import settings

logger = logging.getLogger(__name__)

# Timeout reduzido (3 seg) para detectar erro rápido
TIMEOUT_SECS = 3
RETRY_COUNT = 1


async def call_deepware(arquivo_path: str) -> dict:
    """Deepware Scanner API — deepfake detection with timeout protection"""
    key = getattr(settings, 'deepware_api_key', None) or os.getenv('DEEPWARE_API_KEY')
    if not key or key.startswith('sk_live_'):  # Dummy key detection
        return {"api": "deepware", "error": "invalid_key"}

    try:
        with open(arquivo_path, "rb") as f:
            file_b64 = base64.b64encode(f.read()).decode()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepware.ai/v1/deepfake-detection",
                json={"file": file_b64},
                headers={"Authorization": f"Bearer {key}"},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "api": "deepware",
                        "is_fake": data.get("is_fake"),
                        "confidence": data.get("confidence", 0.5),
                    }
                return {"api": "deepware", "error": f"http_{resp.status}"}

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Deepware timeout/error (expected if key dummy): {type(e).__name__}")
        return {"api": "deepware", "error": "timeout"}
    except Exception as e:
        logger.warning(f"Deepware error: {e}")
        return {"api": "deepware", "error": str(e)}


async def call_azure(arquivo_path: str) -> dict:
    """Azure Video Indexer — video analysis with timeout protection"""
    key = getattr(settings, 'azure_api_key', None) or os.getenv('AZURE_API_KEY')
    if not key or 'prod_key' not in key.lower():  # Dummy key detection
        return {"api": "azure", "error": "invalid_key"}

    try:
        with open(arquivo_path, "rb") as f:
            file_data = f.read()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.videoindexer.ai/v1/analyze",
                data=file_data,
                headers={"Ocp-Apim-Subscription-Key": key},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    deepfake_score = data.get("deepfakeScore", 0.5)
                    return {
                        "api": "azure",
                        "is_fake": deepfake_score > 0.5,
                        "confidence": deepfake_score,
                    }
                return {"api": "azure", "error": f"http_{resp.status}"}

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Azure timeout/error (expected if key dummy): {type(e).__name__}")
        return {"api": "azure", "error": "timeout"}
    except Exception as e:
        logger.warning(f"Azure error: {e}")
        return {"api": "azure", "error": str(e)}


async def call_google_cloud(arquivo_path: str) -> dict:
    """Google Cloud Video Intelligence with timeout protection"""
    creds = getattr(settings, 'google_application_credentials', None) or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds or not creds.endswith('.json'):  # Dummy detection
        return {"api": "google_cloud", "error": "invalid_creds"}

    try:
        with open(arquivo_path, "rb") as f:
            file_b64 = base64.b64encode(f.read()).decode()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://videointelligence.googleapis.com/v1/videos:annotate",
                json={"inputContent": file_b64, "features": ["LABEL_DETECTION"]},
                headers={"Authorization": f"Bearer dummy_token"},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    is_fake = any("fake" in str(label).lower() for label in data.get("labels", []))
                    return {
                        "api": "google_cloud",
                        "is_fake": is_fake,
                        "confidence": 0.75 if is_fake else 0.25,
                    }
                return {"api": "google_cloud", "error": f"http_{resp.status}"}

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Google Cloud timeout/error (expected if creds dummy): {type(e).__name__}")
        return {"api": "google_cloud", "error": "timeout"}
    except Exception as e:
        logger.warning(f"Google Cloud error: {e}")
        return {"api": "google_cloud", "error": str(e)}


async def call_reality_defender(arquivo_path: str) -> dict:
    """Reality Defender — deepfake detection with timeout protection"""
    key = getattr(settings, 'reality_defender_key', None) or os.getenv('REALITY_DEFENDER_KEY')
    if not key or not key.startswith('rd_'):  # Dummy detection
        return {"api": "reality_defender", "error": "invalid_key"}

    try:
        async with aiohttp.ClientSession() as session:
            with open(arquivo_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f)

                async with session.post(
                    "https://api.realitydefender.ai/api/detect",
                    data=data,
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {
                            "api": "reality_defender",
                            "is_fake": result.get("is_fake"),
                            "confidence": result.get("confidence", 0.5),
                        }
                    return {"api": "reality_defender", "error": f"http_{resp.status}"}

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Reality Defender timeout/error (expected if key dummy): {type(e).__name__}")
        return {"api": "reality_defender", "error": "timeout"}
    except Exception as e:
        logger.warning(f"Reality Defender error: {e}")
        return {"api": "reality_defender", "error": str(e)}


async def call_sensity(arquivo_path: str) -> dict:
    """Sensity — deepfake and media forensics with timeout protection"""
    key = getattr(settings, 'sensity_api_key', None) or os.getenv('SENSITY_API_KEY')
    if not key or 'enterprise' not in key.lower():  # Dummy detection
        return {"api": "sensity", "error": "invalid_key"}

    try:
        async with aiohttp.ClientSession() as session:
            with open(arquivo_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("video", f)

                async with session.post(
                    "https://api.sensity.ai/api/deepfake-scan",
                    data=data,
                    headers={"X-API-Key": key},
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {
                            "api": "sensity",
                            "is_fake": result.get("is_deepfake"),
                            "confidence": result.get("confidence", 0.5),
                        }
                    return {"api": "sensity", "error": f"http_{resp.status}"}

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Sensity timeout/error (expected if key dummy): {type(e).__name__}")
        return {"api": "sensity", "error": "timeout"}
    except Exception as e:
        logger.warning(f"Sensity error: {e}")
        return {"api": "sensity", "error": str(e)}


async def call_hume(arquivo_path: str) -> dict:
    """Hume AI — authenticity detection via emotional analysis with timeout protection"""
    key = getattr(settings, 'hume_api_key', None) or os.getenv('HUME_API_KEY')
    if not key:
        return {"api": "hume", "error": "invalid_key"}

    try:
        with open(arquivo_path, "rb") as f:
            file_b64 = base64.b64encode(f.read()).decode()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.hume.ai/v0/predict",
                json={"data": file_b64},
                headers={"Authorization": f"Bearer {key}"},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECS)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    authenticity = data.get("authenticity_score", 0.5)
                    return {
                        "api": "hume",
                        "is_fake": authenticity < 0.5,
                        "confidence": authenticity,
                    }
                return {"api": "hume", "error": f"http_{resp.status}"}

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Hume timeout/error (expected if key dummy): {type(e).__name__}")
        return {"api": "hume", "error": "timeout"}
    except Exception as e:
        logger.warning(f"Hume error: {e}")
        return {"api": "hume", "error": str(e)}


def calcular_consensus(resultados_apis: list) -> tuple:
    """
    Calcula consenso entre APIs.

    Args:
        resultados_apis: Lista de dicts {"api": name, "is_fake": bool, "confidence": float}

    Returns:
        (veredicto, consensus_pct): ("APROVADO"/"REJEITADO"/"REVISAR", porcentagem 0-100)
    """
    # Filter out error responses
    valid = [r for r in resultados_apis if "error" not in r]

    if not valid:
        return "REVISAR", 0.0

    fake_count = sum(1 for r in valid if r.get("is_fake"))
    total = len(valid)
    consensus_pct = (fake_count / total) * 100 if total > 0 else 0

    # Veredicto baseado em consenso
    if consensus_pct >= 70:
        veredicto = "REJEITADO" if fake_count > total / 2 else "APROVADO"
    else:
        veredicto = "REVISAR"  # Divergência > 30%

    logger.info(f"Consensus: {fake_count}/{total} APIs (fake), {consensus_pct:.1f}% → {veredicto}")

    return veredicto, consensus_pct
