from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    email: EmailStr | None = None
