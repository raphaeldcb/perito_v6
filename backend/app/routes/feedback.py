from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.services.database import get_db
from app.middleware.auth import get_current_user
from app.models.feedback import FeedbackReport, FeedbackAttachment
from app.models import User
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import shutil
from pathlib import Path

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

class FeedbackReportRequest(BaseModel):
    title: str
    description: str
    severity: str = "MEDIUM"
    is_in_scope: Optional[bool] = None

class FeedbackReportResponse(BaseModel):
    id: int
    title: str
    description: str
    severity: str
    status: str
    analysis_notes: Optional[str] = None
    created_at: str
    analyzed_at: Optional[str] = None
    implemented_at: Optional[str] = None

VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
FEEDBACK_DIR = "tmp/feedback_attachments"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/report", status_code=201)
async def submit_feedback(
    title: str = Form(...),
    description: str = Form(...),
    severity: str = Form(default="MEDIUM"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit user feedback with optional file attachment."""

    if severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}. Must be one of {VALID_SEVERITIES}")

    attachment_path = None
    if file:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")

        try:
            upload_dir = Path(FEEDBACK_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
            file_path = upload_dir / filename

            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            attachment_path = str(file_path)
        except Exception as e:
            print(f"File upload error: {e}")
            attachment_path = None

    feedback = FeedbackReport(
        user_id=current_user.id,
        title=title,
        description=description,
        severity=severity,
        attachment_path=attachment_path,
        status="PENDING",
        created_ip=None
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return {
        "id": feedback.id,
        "status": "PENDING",
        "message": "Feedback received successfully"
    }

@router.get("/report/{feedback_id}")
async def get_feedback_status(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get feedback report status by ID."""

    feedback = db.query(FeedbackReport).filter(
        FeedbackReport.id == feedback_id,
        FeedbackReport.user_id == current_user.id
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return FeedbackReportResponse(
        id=feedback.id,
        title=feedback.title,
        description=feedback.description,
        severity=feedback.severity,
        status=feedback.status,
        analysis_notes=feedback.analysis_notes,
        created_at=feedback.created_at.isoformat(),
        analyzed_at=feedback.analyzed_at.isoformat() if feedback.analyzed_at else None,
        implemented_at=feedback.implemented_at.isoformat() if feedback.implemented_at else None
    )
