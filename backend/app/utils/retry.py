"""Decorator de retry com backoff exponencial para resiliência.

Uso:
    @retry(max_attempts=5, backoff=2)
    def chamar_api_externa():
        return requests.get("...")

    # Retorna na primeira tentativa bem-sucedida; se todas falharem, levanta a última exception.
"""
import logging
import time
from functools import wraps
from typing import Callable, Type, Tuple, Any, Optional

logger = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """Levantada quando todas as tentativas de retry se esgotam."""
    pass


def retry(
    max_attempts: int = 5,
    backoff: float = 2.0,
    initial_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        Exception,  # Por padrão, tenta novamente em QUALQUER exceção
    ),
    jitter: bool = True,
):
    """
    Decorator que tenta novamente uma função com backoff exponencial.

    Args:
        max_attempts: número máximo de tentativas (padrão: 5)
        backoff: fator multiplicador de delay (padrão: 2.0 → 1s, 2s, 4s, 8s, 16s)
        initial_delay: delay inicial em segundos (padrão: 1.0)
        retryable_exceptions: tupla de exceções que disparam retry (padrão: Exception)
        jitter: adiciona aleatoriedade ao delay para evitar "thundering herd"

    Exemplo:
        @retry(max_attempts=5, backoff=2, initial_delay=1)
        def chamar_api():
            return requests.get("https://api.example.com")

        resposta = chamar_api()  # Tenta até 5 vezes com delays 1s, 2s, 4s, 8s, 16s
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(
                        f"[{func.__name__}] Tentativa {attempt}/{max_attempts}"
                    )
                    return func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"[{func.__name__}] Tentativa {attempt}/{max_attempts} falhou: "
                        f"{type(e).__name__}: {str(e)[:100]}"
                    )

                    # Se foi a última tentativa, não aguarda — levanta logo
                    if attempt >= max_attempts:
                        logger.error(
                            f"[{func.__name__}] Todas as {max_attempts} tentativas "
                            f"se esgotaram. Levantando: {type(e).__name__}"
                        )
                        raise

                    # Calcula delay com backoff exponencial + jitter opcional
                    if jitter:
                        import random
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay

                    logger.info(
                        f"[{func.__name__}] Aguardando {actual_delay:.1f}s "
                        f"antes da tentativa {attempt + 1}"
                    )
                    time.sleep(actual_delay)

                    # Próximo delay = backoff exponencial
                    delay *= backoff

            # Fallback (não deveria chegar aqui)
            if last_exception:
                raise last_exception
            raise RetryExhausted(f"Todas as {max_attempts} tentativas falharam")

        return wrapper
    return decorator
