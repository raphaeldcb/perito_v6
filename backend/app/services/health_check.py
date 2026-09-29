"""Health check com verificações profundas de componentes críticos."""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

try:
    import redis
except ImportError:
    redis = None  # Redis is optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.services.database import SessionLocal
from app.models import Job

logger = logging.getLogger(__name__)

# Simple cache for health check results (5s TTL)
_health_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 5


async def check_db() -> tuple[str, str]:
    """Verifica conexão com DB via query de teste."""
    try:
        db = SessionLocal()
        try:
            # Test query
            db.execute(text("SELECT 1"))
            db.commit()
            return "ok", None
        except Exception as e:
            return "error", str(e)
        finally:
            db.close()
    except Exception as e:
        return "error", str(e)


async def check_qwen() -> tuple[str, str]:
    """Verifica se Qwen (Ollama) está respondendo com timeout de 5s."""
    try:
        # Endpoint de health do Ollama
        url = f"{settings.ollama_url}/api/tags"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return "ok", None
        else:
            return "error", f"HTTP {response.status_code}"
    except requests.Timeout:
        return "error", "Timeout after 5s"
    except Exception as e:
        return "error", str(e)


async def check_queue() -> tuple[str, str, int]:
    """Verifica saúde da fila (< 1000 jobs "na_fila")."""
    try:
        db = SessionLocal()
        try:
            count = db.query(Job).filter(Job.status == "na_fila").count()
            if count >= 1000:
                return "warning", f"Queue has {count} pending jobs", count
            return "ok", None, count
        finally:
            db.close()
    except Exception as e:
        return "error", str(e), 0


async def check_stale_jobs() -> tuple[str, str, int]:
    """Verifica e resets jobs "processando" > 10 min marcando como erro."""
    try:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            threshold = now - timedelta(minutes=10)

            # Encontra jobs "processando" que começaram há > 10 min
            stale_jobs = db.query(Job).filter(
                Job.status == "processando",
                Job.iniciado_em < threshold
            ).all()

            reset_count = 0
            for job in stale_jobs:
                job.status = "erro"
                job.erro = f"Stale job reset at {now.isoformat()} (running > 10 min)"
                reset_count += 1

            if reset_count > 0:
                db.commit()
                logger.warning(f"🔧 Reset {reset_count} stale jobs")

            return "ok", None, reset_count
        finally:
            db.close()
    except Exception as e:
        return "error", str(e), 0


async def check_redis() -> Tuple[str, Optional[str]]:
    """Verifica conexão com Redis (opcional)."""
    try:
        if not redis:
            return "skipped", "Redis module not installed"

        redis_url = getattr(settings, "redis_url", None)
        if not redis_url:
            return "skipped", "Redis not configured"

        r = redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=True)
        r.ping()
        return "ok", None
    except Exception as e:
        return "error", str(e)


async def check_resilience() -> Dict[str, Any]:
    """Verifica métricas de resiliência (circuit breakers, retries)."""
    try:
        from app.core.resilience import get_resilience_metrics
        metrics = get_resilience_metrics()
        return metrics
    except Exception as e:
        logger.warning(f"Failed to get resilience metrics: {e}")
        return {"status": "error", "detail": str(e)}


async def get_health_status() -> Dict[str, Any]:
    """Retorna status completo de saúde do sistema com cache de 5s."""
    global _health_cache, _cache_timestamp

    # Verificar cache
    now = datetime.utcnow()
    if _cache_timestamp and (now - _cache_timestamp).total_seconds() < CACHE_TTL_SECONDS:
        return _health_cache

    # Executar verificações
    db_status, db_error = await check_db()
    qwen_status, qwen_error = await check_qwen()
    queue_status, queue_error, queue_count = await check_queue()
    stale_status, stale_error, stale_reset_count = await check_stale_jobs()
    redis_status, redis_error = await check_redis()
    resilience_metrics = await check_resilience()

    # Sistema é healthy se DB e Qwen estão ok
    # Queue warning não é critical
    overall_status = (
        "healthy"
        if db_status == "ok" and qwen_status == "ok"
        else "unhealthy"
    )

    # Se algum componente crítico está em erro, retorna 503
    http_status = 200 if overall_status == "healthy" else 503

    result = {
        "status": overall_status,
        "components": {
            "db": db_status if db_status == "ok" else f"error: {db_error}",
            "qwen": qwen_status if qwen_status == "ok" else f"error: {qwen_error}",
            "queue": queue_status if queue_status == "ok" else f"warning: {queue_error}",
            "redis": redis_status if redis_status == "ok" else f"error: {redis_error}",
            "resilience": resilience_metrics,
        },
        "metrics": {
            "queue_count": queue_count,
            "stale_jobs_reset": stale_reset_count,
        },
        "timestamp": datetime.utcnow().isoformat(),
        "http_status": http_status,
    }

    # Cache the result
    _health_cache = result
    _cache_timestamp = now

    return result
