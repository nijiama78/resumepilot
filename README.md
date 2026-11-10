# ResumePilot — AI 简历诊断平台

上传简历 PDF，粘贴目标岗位 JD，获得 ATS 评分、关键词匹配分析与可执行的修改建议。

- **前端**：Vue 3 + TypeScript + Vite + Pinia + Vue Router
- **后端**：FastAPI + SQLModel（SQLite，可切换 PostgreSQL）
- **分析引擎**：规则引擎兜底（零配置可跑）/ 大模型分析（配置 `LLM_API_KEY` 后自动切换）
- **认证**：JWT + bcrypt 密码哈希

## 目录结构

```
resumepilot/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI 入口与全部 API 路由
│   │   ├── models.py      # User / Resume / Analysis 数据表
│   │   ├── auth.py        # JWT 签发校验 + bcrypt
│   │   ├── analyzer.py    # 分析引擎（规则引擎 + LLM 适配）
│   │   ├── parser.py      # PDF / TXT 文本提取（PyMuPDF）
│   │   ├── config.py      # 环境变量配置
│   │   ├── db.py          # 数据库连接
│   │   └── schemas.py     # 请求/响应模型
│   ├── tests/test_api.py  # 核心接口集成测试
│   ├── requirements.txt
│   └── sample_resume.txt  # 测试用示例简历
├── frontend/
│   └── src/
│       ├── views/         # 登录/注册/上传/结果/历史 五个页面
│       ├── stores/auth.ts # Pinia 认证状态
│       ├── api.ts         # fetch 封装（自动携带 Token）
│       └── router.ts      # 路由与登录守卫
└── tools/uv.exe           # 包管理器（本机 pip 受限时的替代）
```

## 快速开始

前置：Python 3.10+、Node.js 18+

### 1. 后端（终端 A）

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# 若 pip 无法访问网络，可用项目内置 uv：
# ../tools/uv.exe pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

### 2. 前端（终端 B）

```bash
cd frontend
npm install
npm run dev        # 打开 http://localhost:5173
```

### 3. 运行测试

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/ -q
```

### 4. 启用 AI 分析（可选）

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（OpenAI 兼容接口）
```

不配置也能完整使用：自动使用内置规则引擎（联系方式/篇幅/量化成果/JD 关键词/行为动词五个维度评分）。

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册 `{email, password}` |
| POST | `/api/auth/login` | 登录（form 格式），返回 JWT |
| GET | `/api/auth/me` | 当前用户（需 Token） |
| POST | `/api/resumes/upload` | 上传简历 PDF/TXT（需 Token） |
| GET | `/api/resumes` | 我的简历列表（需 Token） |
| POST | `/api/analyze` | 分析 `{resume_id, job_description?}`（需 Token） |
| GET | `/api/analyses` | 分析历史（需 Token） |
| GET | `/api/analyses/{id}` | 单次分析详情（需 Token） |
| POST | `/api/chat` | RAG 对话追问 `{resume_id, question}`，SSE 流式返回（需 Token） |
| GET | `/api/health` | 健康检查 |

交互式 API 文档：http://localhost:8000/docs （FastAPI 自动生成）

## 迭代路线

- [x] W1 脚手架 + JWT 认证
- [x] W2 简历上传 + PDF/TXT 解析
- [x] W3 分析主线（规则引擎 + LLM 适配）
- [x] W4 RAG 对话式修改建议（简历切块 → 向量检索 Top-K → SSE 流式生成；无 Key 时规则兜底）
- [x] W5 评分历史 Dashboard（Chart.js 可视化：评分趋势 / 五维雷达 / 短板关键词频次）
- [x] W6 Docker Compose + GitHub Actions CI（pytest + 前端构建）

## Docker 部署（W6）

前置：安装 Docker Desktop

```bash
# 项目根目录（resumepilot/）下执行，一条命令启动前后端
docker compose up --build

# 访问 http://localhost:8080
```

- 前端：nginx 托管构建产物，并把 `/api` 反向代理到后端容器（SSE 流式已配置关闭缓冲）
- 后端：FastAPI + SQLite（数据挂在 `resumepilot-data` 卷，重建容器不丢数据）
- 生产部署时通过环境变量覆盖：`SECRET_KEY`、`ALLOWED_ORIGINS`（你的前端域名）、`LLM_API_KEY`

## 云部署指引（免费方案）

1. **代码上 GitHub**：`git init && git add . && git commit -m "init"` 后推送（推 main 分支会自动触发 CI 跑测试）
2. **后端 → [Render](https://render.com)**：New Web Service → 选仓库 → Root Directory 填 `backend` → 自动识别 Dockerfile → 环境变量填 `SECRET_KEY`、`ALLOWED_ORIGINS=https://你的前端域名`、`LLM_API_KEY`（可选）；免费档会休眠，首次访问稍慢
3. **前端 → [Vercel](https://vercel.com)**：Import 仓库 → Root Directory 填 `frontend` → 环境变量 `VITE_API_BASE=https://你的render后端地址`
4. 把 Vercel 域名回填到后端 `ALLOWED_ORIGINS`，完成

> `.gitignore` 已配置，排除 `.venv/`、`node_modules/`、`*.db`、`.env` 等，可直接推送。
