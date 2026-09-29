"""
Rate Limiting Middleware (Security P1 — Task 3)

Implements per-endpoint and per-IP rate limiting:
- Login: 5 requests per minute per IP (brute force protection)
- Comunicacoes: 50 requests per minute per IP
- API default: 100 requests per minute per IP

Uses slowapi with in-memory storage for dev, Redis for production.
Returns 429 Too Many Requests with Retry-After header.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter (in-memory for dev, Redis for production)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Global fallback for /api/v1/*
    storage_uri="memory://",  # In-memory for dev; production should use Redis
)

# Custom rate limits per endpoint
RATE_LIMITS = {
    "login": "5/minute",              # Brute force protection
    "comunicacoes": "50/minute",      # Judicial communications
    "api_default": "100/minute",      # Default for /api/v1/* endpoints
}
