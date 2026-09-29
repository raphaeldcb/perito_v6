"""Circuit breaker para proteção de APIs externas — CLOSED → OPEN → HALF_OPEN.

Estados:
- CLOSED: funcionando normalmente (padrão)
- OPEN: serviço indisponível; fail-fast (retorna erro sem tentar)
- HALF_OPEN: testando se o serviço recuperou (tenta 1 requisição)

Uso:
    from app.utils.circuit_breaker import CircuitBreaker

    # Instância por serviço (reutilizável)
    breaker_qwen = CircuitBreaker("qwen", threshold=5, timeout=60)

    @breaker_qwen.call()  # Decorator
    def chamar_qwen():
        return requests.post(...)

    # Ou chamar diretamente
    try:
        resultado = breaker_qwen.call_function(chamar_qwen)
    except CircuitBreakerOpen:
        logger.error("Qwen indisponível; retornando fallback")
        resultado = fallback()
"""
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Callable, Any, Optional

# HTTPException é importado no contexto de uso

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Estados do circuit breaker."""
    CLOSED = "CLOSED"  # Funcionando normalmente
    OPEN = "OPEN"  # Indisponível; fail-fast
    HALF_OPEN = "HALF_OPEN"  # Testando recuperação


class CircuitBreakerOpen(Exception):
    """Levantada quando circuit breaker está OPEN."""
    pass


class CircuitBreaker:
    """
    Circuit breaker para proteção de APIs externas.

    Args:
        name: identificador do serviço (ex: "qwen", "inter", "djen")
        threshold: número de erros consecutivos antes de abrir (padrão: 5)
        timeout: segundos que o circuito fica aberto antes de testar (padrão: 60)
        half_open_max_calls: máx de chamadas na fase HALF_OPEN antes de reabrir (padrão: 1)
    """

    def __init__(
        self,
        name: str,
        threshold: int = 5,
        timeout: int = 60,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.threshold = threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

    def _reset(self):
        """Reseta o estado para CLOSED."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None
        logger.info(f"Circuit breaker '{self.name}' CLOSED (reset)")

    def _open(self):
        """Abre o circuito."""
        self.state = CircuitBreakerState.OPEN
        self.opened_at = datetime.now()
        logger.error(
            f"Circuit breaker '{self.name}' OPEN "
            f"({self.failure_count} erros consecutivos)"
        )

    def _half_open(self):
        """Muda para HALF_OPEN para testar recuperação."""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        logger.warning(
            f"Circuit breaker '{self.name}' HALF_OPEN "
            f"(testando recuperação após {self.timeout}s)"
        )

    def call_function(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executa uma função através do circuit breaker.

        Args:
            func: função a executar
            *args, **kwargs: argumentos para a função

        Returns:
            Resultado da função

        Raises:
            CircuitBreakerOpen: se circuit breaker está aberto
            Exception: qualquer exceção lançada por `func`
        """
        # Se está OPEN, verifica se já passou o timeout
        if self.state == CircuitBreakerState.OPEN:
            if self.opened_at and datetime.now() < self.opened_at + timedelta(seconds=self.timeout):
                # Ainda não passou o timeout; fail-fast
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' está OPEN. "
                    f"Próxima tentativa em "
                    f"{(self.opened_at + timedelta(seconds=self.timeout) - datetime.now()).total_seconds():.1f}s"
                )
            else:
                # Timeout expirou; tenta mudar para HALF_OPEN
                self._half_open()

        # Tenta executar a função
        try:
            result = func(*args, **kwargs)

            # Sucesso!
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Se estava testando, fechamos o circuito
                self._reset()
            else:
                # Se estava CLOSED, apenas reseta o contador de falhas
                self.failure_count = 0

            logger.debug(f"Circuit breaker '{self.name}' sucesso")
            return result

        except Exception as e:
            # Falha
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            logger.warning(
                f"Circuit breaker '{self.name}' falha {self.failure_count}/{self.threshold}: "
                f"{type(e).__name__}: {str(e)[:100]}"
            )

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Em HALF_OPEN, qualquer erro reabre
                self._open()
            elif self.failure_count >= self.threshold:
                # Em CLOSED, após threshold erros abre
                self._open()

            raise

    def call(self) -> Callable:
        """Decorator para usar em funções."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                return self.call_function(func, *args, **kwargs)
            return wrapper
        return decorator

    def get_status(self) -> dict:
        """Retorna status atual do circuit breaker."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "threshold": self.threshold,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


# Registry global de circuit breakers (para reutilização)
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    threshold: int = 5,
    timeout: int = 60,
) -> CircuitBreaker:
    """
    Obtém ou cria um circuit breaker reutilizável.

    Args:
        name: identificador único do serviço
        threshold: erros antes de abrir
        timeout: segundos que fica aberto

    Returns:
        Instância de CircuitBreaker (singleton por name)
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, threshold, timeout)
    return _circuit_breakers[name]


def circuit_breaker_status() -> dict[str, dict]:
    """Retorna status de todos os circuit breakers."""
    return {
        name: breaker.get_status()
        for name, breaker in _circuit_breakers.items()
    }
