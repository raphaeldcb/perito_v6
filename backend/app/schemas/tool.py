from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class ToolCreate(BaseModel):
    name: str
    title: str
    description: str | None = None
    url: str
    icon: str | None = None
    component: str | None = None
    access_level: Literal["public", "user", "power_user", "admin"] = "user"
    version: str = "1.0.0"
    config: str | None = None


class ToolRead(BaseModel):
    id: int
    name: str
    title: str
    description: str | None
    url: str
    icon: str | None
    component: str | None
    access_level: str
    is_active: bool
    version: str
    config: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    url: str | None = None
    access_level: str | None = None
    is_active: bool | None = None
    version: str | None = None
