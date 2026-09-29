from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import AuditLog, User
from app.services import get_db
from app.middleware import get_current_user
from app.config import settings

router = APIRouter()


@router.get("")
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name not in ["admin", "power_user"]:
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")

    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs


@router.get("/stats")
async def audit_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view stats")

    total_logs = db.query(AuditLog).count()
    today_logs = db.query(AuditLog).filter(
        AuditLog.created_at >= datetime.utcnow() - timedelta(days=1)
    ).count()

    return {
        "total_logs": total_logs,
        "today_logs": today_logs,
        "retention_days": settings.audit_retention_days,
    }
