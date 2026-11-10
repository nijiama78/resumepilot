"""数据表定义（SQLModel = Pydantic + SQLAlchemy）。"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=_utcnow)


class Resume(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    filename: str
    content_text: str  # 从 PDF/TXT 提取的纯文本
    created_at: datetime = Field(default_factory=_utcnow)


class Analysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    resume_id: int = Field(foreign_key="resume.id", index=True)
    job_description: str = ""           # 目标岗位 JD（可空）
    score: int                          # 总分 0-100
    summary: str                        # 总体评价
    details_json: str                   # 维度得分、建议、关键词等 JSON 字符串
    engine: str                         # "rule"（规则引擎）或 "llm"（大模型）
    created_at: datetime = Field(default_factory=_utcnow)
