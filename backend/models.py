"""Pydantic schemas for request / response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Auth ────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=4)
    full_name: str
    role: str = "user"
    department: str = "general"
    phone: str = ""


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    user_id: int


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    department: str
    phone: str
    is_active: bool
    created_at: Optional[datetime] = None
    assigned_staff_id: Optional[int] = None

    class Config:
        from_attributes = True


# ─── Chat ────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    access_decision: Optional[str] = None
    sources: Optional[list[str]] = None


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    tool_used: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Admin ───────────────────────────────────────────────────────────────────


class AssignStaff(BaseModel):
    user_id: int
    staff_id: int


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ─── Documents ───────────────────────────────────────────────────────────────


class DocumentUpload(BaseModel):
    title: str
    content: str
    category: str = "general"
    access_level: str = "all"


class DocumentInfo(BaseModel):
    id: int
    title: str
    category: str
    access_level: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
