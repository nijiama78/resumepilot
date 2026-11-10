"""API 请求/响应模型。"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResumeOut(BaseModel):
    id: int
    filename: str
    content_text: str
    created_at: datetime


class AnalyzeRequest(BaseModel):
    resume_id: int
    job_description: str = ""


class AnalysisOut(BaseModel):
    id: int
    resume_id: int
    filename: Optional[str] = None
    job_description: str
    score: int
    summary: str
    engine: str
    details: dict[str, Any]
    created_at: datetime


class ChatRequest(BaseModel):
    resume_id: int
    question: str = Field(..., min_length=1, max_length=500)
