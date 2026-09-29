from pydantic import BaseModel
from datetime import datetime


class PermissionCreate(BaseModel):
    role_id: int
    action: str
    resource: str
    description: str | None = None


class PermissionRead(BaseModel):
    id: int
    role_id: int
    action: str
    resource: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
