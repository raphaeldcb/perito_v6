import functools
import time

def retry(max_attempts=3, backoff_factor=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(backoff_factor ** attempt)
        return wrapper
    return decorator

class CircuitBreakerOpen(Exception):
    pass

def get_circuit_breaker(name):
    return None
