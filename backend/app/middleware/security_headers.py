"""
Phase 5: Security Headers + WAF Configuration
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de segurança críticos"""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Content Security Policy (CSP)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (Permissions-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), microphone=(), "
            "geolocation=(), payment=(), usb=()"
        )
        
        # HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        # Remove server info
        # Nota: MutableHeaders (starlette 0.36.3, versão pinada em
        # requirements_v6.txt) não tem .pop() — só __delitem__ (que já é
        # no-op seguro se a chave não existir). .pop() aqui derrubava TODA
        # requisição que passasse por este middleware com AttributeError
        # (bug pré-existente, achado ao rodar os testes da Task 2).
        del response.headers["Server"]
        response.headers["X-Powered-By"] = "FastAPI"
        
        return response
