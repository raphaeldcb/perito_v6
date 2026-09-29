"""Middleware de auditoria - registra login/logout, erros de acesso, operações admin, uploads/downloads."""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Configurações de auditoria
AUDIT_LOG_DIR = Path("logs")
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "audit.log"
AUDIT_RETENTION_DAYS = 30


def ensure_audit_dir():
    """Garante que o diretório de logs existe."""
    AUDIT_LOG_DIR.mkdir(exist_ok=True)


def rotate_audit_logs():
    """Rotaciona logs diários (não apaga, apenas marca novo arquivo)."""
    ensure_audit_dir()
    if AUDIT_LOG_FILE.exists():
        file_size = AUDIT_LOG_FILE.stat().st_size
        # Se arquivo > 100MB, rotaciona
        if file_size > 100 * 1024 * 1024:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rotated = AUDIT_LOG_DIR / f"audit_{timestamp}.log"
            AUDIT_LOG_FILE.rename(rotated)
            logger.info(f"📋 Audit log rotated: {rotated}")


def cleanup_old_audit_logs():
    """Remove audit logs mais antigos que retention days."""
    ensure_audit_dir()
    cutoff = datetime.utcnow() - timedelta(days=AUDIT_RETENTION_DAYS)

    for log_file in AUDIT_LOG_DIR.glob("audit*.log"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
                logger.info(f"🗑️ Deleted old audit log: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup log {log_file}: {e}")


def log_audit_event(
    action: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    method: str = "",
    path: str = "",
    status_code: int = 200,
    resource: str = "",
    details: dict = None,
    ip: str = "",
):
    """Registra um evento de auditoria em JSON."""
    ensure_audit_dir()
    rotate_audit_logs()

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "user_id": user_id,
        "user_email": user_email,
        "method": method,
        "path": path,
        "status_code": status_code,
        "resource": resource,
        "ip": ip,
        **(details or {}),
    }

    try:
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware que registra eventos de auditoria."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Obter IP do cliente
        client_ip = request.client.host if request.client else "unknown"
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()

        # Obter usuário (se autenticado)
        user_id = None
        user_email = None
        try:
            if hasattr(request.state, "user"):
                user_id = request.state.user.id
                user_email = request.state.user.email
        except:
            pass

        # Chamadas à rota de saúde não são auditadas
        if request.url.path == "/health":
            return await call_next(request)

        # Processa a requisição
        response = await call_next(request)

        # Log de 401/403 (acesso negado)
        if response.status_code in [401, 403]:
            log_audit_event(
                action="access_denied" if response.status_code == 403 else "unauthorized",
                user_id=user_id,
                user_email=user_email,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip=client_ip,
            )

        # Log de operações admin (create/update/delete em processos, vistoria, etc)
        if (
            request.method in ["POST", "PUT", "DELETE"]
            and any(
                pattern in request.url.path
                for pattern in [
                    "/api/v1/processos",
                    "/api/v1/vistorias",
                    "/api/v1/usuarios",
                    "/api/v1/parametros",
                ]
            )
        ):
            log_audit_event(
                action=f"admin_{request.method.lower()}",
                user_id=user_id,
                user_email=user_email,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                resource=request.url.path.split("/")[-1] if "/" in request.url.path else "",
                ip=client_ip,
            )

        # Log de upload/download
        if "upload" in request.url.path or request.method == "POST" and "arquivo" in request.url.path:
            log_audit_event(
                action="upload",
                user_id=user_id,
                user_email=user_email,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip=client_ip,
            )

        if "download" in request.url.path or request.method == "GET" and any(
            pattern in request.url.path for pattern in ["/pdf", "/arquivo", "/documento"]
        ):
            log_audit_event(
                action="download",
                user_id=user_id,
                user_email=user_email,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip=client_ip,
            )

        return response
