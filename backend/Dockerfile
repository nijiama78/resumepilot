# ---------- 构建阶段 ----------
FROM python:3.13-slim AS builder

WORKDIR /app

# uv 官方安装脚本装到 /usr/local/bin，走国内镜像加速
ADD --chmod=755 https://ghproxy.net/https://github.com/astral-sh/uv/releases/latest/download/uv-installer.sh /tmp/uv-installer.sh
RUN sh /tmp/uv-installer.sh && cp /root/.local/bin/uv /usr/local/bin/uv

COPY requirements.txt .
# 只装运行时依赖到 /deps
RUN uv pip install --system --target /deps -r requirements.txt

# ---------- 运行阶段 ----------
FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /deps /usr/local/lib/python3.13/site-packages
COPY . .

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/resumepilot.db

# SQLite 数据挂到 /data，容器重建不丢数据
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
