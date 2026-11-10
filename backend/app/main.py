"""ResumePilot 后端主入口。

API 概览：
- POST /api/auth/register      注册
- POST /api/auth/login         登录（返回 JWT）
- GET  /api/auth/me            当前用户信息
- POST /api/resumes/upload     上传简历（PDF/TXT）
- GET  /api/resumes            我的简历列表
- POST /api/analyze            发起分析（简历 + 可选 JD）
- GET  /api/analyses           分析历史
- GET  /api/analyses/{id}      单次分析详情
"""
import json
import re

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from . import analyzer, rag, schemas
from .auth import create_access_token, get_current_user, hash_password, verify_password
from .config import settings
from .db import get_session, init_db
from .models import Analysis, Resume, User
from .parser import extract_text

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = FastAPI(title="ResumePilot API", version="0.1.0")

# 开发环境允许 Vite dev server 跨域；生产环境用 ALLOWED_ORIGINS 环境变量覆盖
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------- 认证 ----------

@app.post("/api/auth/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, session: Session = Depends(get_session)):
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")
    user = User(email=email, hashed_password=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == form.username.strip().lower())).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    return schemas.TokenResponse(access_token=create_access_token(user.id))


@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ---------- 简历 ----------

@app.post("/api/resumes/upload", response_model=schemas.ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 5MB 限制")
    text = extract_text(file.filename or "", file_bytes)

    resume = Resume(user_id=user.id, filename=file.filename or "resume", content_text=text)
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


@app.get("/api/resumes", response_model=list[schemas.ResumeOut])
def list_resumes(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    resumes = session.exec(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.id.desc())
    ).all()
    return resumes


# ---------- 分析 ----------

@app.post("/api/analyze", response_model=schemas.AnalysisOut, status_code=201)
def analyze_resume(
    payload: schemas.AnalyzeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    resume = session.get(Resume, payload.resume_id)
    if not resume or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="简历不存在")

    result, engine = analyzer.analyze(resume.content_text, payload.job_description.strip())

    record = Analysis(
        resume_id=resume.id,
        job_description=payload.job_description.strip(),
        score=int(result.get("score", 0)),
        summary=str(result.get("summary", "")),
        details_json=json.dumps(result, ensure_ascii=False),
        engine=engine,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return schemas.AnalysisOut(
        id=record.id,
        resume_id=resume.id,
        filename=resume.filename,
        job_description=record.job_description,
        score=record.score,
        summary=record.summary,
        engine=record.engine,
        details=json.loads(record.details_json),
        created_at=record.created_at,
    )


@app.get("/api/analyses", response_model=list[schemas.AnalysisOut])
def list_analyses(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(Analysis, Resume)
        .join(Resume, Analysis.resume_id == Resume.id)
        .where(Resume.user_id == user.id)
        .order_by(Analysis.id.desc())
    ).all()
    return [
        schemas.AnalysisOut(
            id=a.id,
            resume_id=a.resume_id,
            filename=r.filename,
            job_description=a.job_description,
            score=a.score,
            summary=a.summary,
            engine=a.engine,
            details=json.loads(a.details_json),
            created_at=a.created_at,
        )
        for a, r in rows
    ]


@app.get("/api/analyses/{analysis_id}", response_model=schemas.AnalysisOut)
def get_analysis(
    analysis_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    row = session.exec(
        select(Analysis, Resume)
        .join(Resume, Analysis.resume_id == Resume.id)
        .where(Analysis.id == analysis_id, Resume.user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    a, r = row
    return schemas.AnalysisOut(
        id=a.id,
        resume_id=a.resume_id,
        filename=r.filename,
        job_description=a.job_description,
        score=a.score,
        summary=a.summary,
        engine=a.engine,
        details=json.loads(a.details_json),
        created_at=a.created_at,
    )


# ---------- RAG 对话 ----------

@app.post("/api/chat")
async def chat(
    payload: schemas.ChatRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """对指定简历发起对话式追问，SSE 流式返回答案。

    管线：简历切块 → 向量检索 Top-K 片段 → LLM 流式生成（无 Key 时规则兜底）。
    """
    resume = session.get(Resume, payload.resume_id)
    if not resume or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 取该简历最近一次分析作为诊断上下文
    last = session.exec(
        select(Analysis).where(Analysis.resume_id == resume.id).order_by(Analysis.id.desc())
    ).first()
    context: dict = {"score": None, "dimensions": {}, "missing_keywords": [], "suggestions": []}
    if last:
        details = json.loads(last.details_json)
        context = {
            "score": last.score,
            "dimensions": details.get("dimensions", {}),
            "missing_keywords": details.get("missing_keywords", []),
            "suggestions": details.get("suggestions", []),
        }

    source = rag.stream_answer(resume.content_text, payload.question.strip(), context)
    return StreamingResponse(
        rag.sse_wrap(source),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
