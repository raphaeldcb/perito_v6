from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role_id: int


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    role_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    role_id: int | None = None
