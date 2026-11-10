"""核心接口集成测试：注册 -> 登录 -> 上传 -> 分析 -> 历史。"""
import io
import os
import sys

import pytest
from fastapi.testclient import TestClient

# 使用独立测试数据库
os.environ["DATABASE_URL"] = "sqlite:///./test_resumepilot.db"
os.environ["SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

client = TestClient(app)

SAMPLE_RESUME = """张三
邮箱: zhangsan@example.com  电话: 13812345678

教育背景
某某大学 计算机科学 本科 2022-2026

项目经历
1. 全栈电商平台
主导基于 FastAPI + React 的电商系统开发，实现 JWT 认证与支付集成；
优化数据库索引，接口响应时间降低 60%，支撑 1000+ 日活用户。

2. 实时聊天应用
独立设计 WebSocket 消息协议，实现单服务 500 并发连接，消息延迟低于 100ms。

技能
Python、TypeScript、React、Vue、FastAPI、MySQL、Redis、Docker
"""


@pytest.fixture(autouse=True)
def clean_db():
    from app.db import engine, init_db
    from sqlmodel import SQLModel
    init_db()
    yield
    SQLModel.metadata.drop_all(engine)


def test_register_login_and_full_flow():
    # 注册
    r = client.post("/api/auth/register", json={"email": "t@t.com", "password": "123456"})
    assert r.status_code == 201, r.text

    # 重复注册 -> 409
    r = client.post("/api/auth/register", json={"email": "t@t.com", "password": "123456"})
    assert r.status_code == 409

    # 登录
    r = client.post("/api/auth/login", data={"username": "t@t.com", "password": "123456"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 当前用户
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "t@t.com"

    # 上传 TXT 简历
    files = {"file": ("resume.txt", io.BytesIO(SAMPLE_RESUME.encode("utf-8")), "text/plain")}
    r = client.post("/api/resumes/upload", files=files, headers=headers)
    assert r.status_code == 201, r.text
    resume_id = r.json()["id"]

    # 分析（带 JD）
    jd = "招聘 Python 全栈工程师，要求熟悉 FastAPI、Redis、Docker，有电商经验优先。"
    r = client.post("/api/analyze", json={"resume_id": resume_id, "job_description": jd}, headers=headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert 0 <= data["score"] <= 100
    assert data["engine"] in ("rule", "llm")
    assert data["details"]["dimensions"]
    assert data["details"]["suggestions"]

    # 历史列表
    r = client.get("/api/analyses", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # 详情
    r = client.get(f"/api/analyses/{data['id']}", headers=headers)
    assert r.status_code == 200

    # 未认证访问被拒
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_bad_email_and_short_password():
    r = client.post("/api/auth/register", json={"email": "not-an-email", "password": "123456"})
    assert r.status_code == 400
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "123"})
    assert r.status_code == 422
