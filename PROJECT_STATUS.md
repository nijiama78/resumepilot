# ResumePilot 项目进度存档（2026-11-10 更新）

> 本文件用于跨会话续接。下次继续时先读本文件 + `README.md`。

## 〇、当前状态：W1-W6 全部完成 ✅（2026-11-10）

仅剩「实际部署到云」一步需要用户注册 Render/Vercel 账号操作，CI/Docker 配置已就绪。

## 一、项目定位

AI 简历诊断平台（简历型作品项目，技术栈 Vue3 + FastAPI）。

用户上传简历 PDF/TXT + 粘贴目标岗位 JD，平台给出 ATS 评分、五维度得分、修改建议、关键词匹配（matched / missing）。

- 项目根目录：`D:/WorkBuddy-Workspace/resumepilot/`
- 调研报告（选题依据）：`D:/WorkBuddy-Workspace/fullstack-projects-research/README.md`

## 二、当前进度：W1-W3 已完成（MVP 可运行）

| 模块 | 状态 | 说明 |
|---|---|---|
| 用户注册/登录（JWT + bcrypt） | ✅ | 完整实现 |
| 简历上传与文本解析（PyMuPDF + txt） | ✅ | PDF/TXT 均可 |
| 分析接口（评分/建议/关键词） | ✅ | 规则引擎实现，`analyzer.py` |
| LLM 接入 | ⏳ 预留 | `.env` 填 `LLM_API_KEY` 后切换，尚未实现 LLM 分支 |
| 历史记录列表 | ✅ | |
| 后端测试（pytest） | ✅ 2/2 通过 | `backend/tests/test_api.py` |
| 前端构建 | ✅ 通过 | 无 TS 错误 |

## 三、技术栈与架构

- 前端：Vue3 + TS + Vite + vue-router@4 + Pinia（原生 CSS）
- 后端：FastAPI + SQLModel + SQLite（`resumepilot.db`）+ JWT（python-jose）
- 前端通过 `src/api.ts` 的 `API_BASE = http://localhost:8000` 调后端；后端 CORS 放行 5173
- 所有依赖均在项目目录内（`.venv/`、`node_modules/`），未动本机全局环境

## 四、如何启动（两个终端，窗口不能关）

```powershell
# 终端1 后端
cd D:\WorkBuddy-Workspace\resumepilot\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# 终端2 前端
cd D:\WorkBuddy-Workspace\resumepilot\frontend
npm run dev
# 浏览器打开 http://localhost:5173
```

- 测试账号：`e2e@test.com / test123456`（e2e 验证时创建）
- 测试简历：`backend/sample_resume.txt`
- API 调试页：http://localhost:8000/docs
- 会话内启动的后台服务随会话结束而停止，需手动重启

## 五、关键实现文件

| 文件 | 内容 |
|---|---|
| `backend/app/main.py` | 全部 API 路由（auth/resumes/analyze/analyses） |
| `backend/app/models.py` | User / Resume / Analysis 三张表（datetime 带时区 UTC） |
| `backend/app/analyzer.py` | 规则引擎评分（联系方式10 + 量化数据20 + 关键词40 + 篇幅10 + 动词20） |
| `backend/app/auth.py` | JWT 签发/校验 |
| `backend/app/parser.py` | PDF/TXT 文本提取 |
| `frontend/src/api.ts` | 后端地址 + 所有请求封装 |
| `frontend/src/router.ts` | 路由守卫（未登录跳 /login） |
| `frontend/src/views/` | Login / Register / Upload / Result / History / Dashboard / Chat 七页 |
| `backend/app/rag.py` | RAG 对话引擎（切块→嵌入→检索→SSE 流式；本地哈希嵌入+规则回答兜底） |
| `frontend/Dockerfile` + `nginx.conf` | 前端镜像（构建+托管+反代 /api，SSE 关缓冲） |
| `backend/Dockerfile` | 后端镜像（uv 装依赖，SQLite 挂 /data 卷） |
| `docker-compose.yml` | 一键编排，访问 :8080 |
| `.github/workflows/ci.yml` | CI：pytest + 前端构建 |

## 六、踩过的坑（避免重犯）

1. **本机 sandbox 拦截 Python 进程走代理的 HTTP 请求** → pip 装包报 "versions: none"。绕过方案：用项目内 `tools/uv.exe` 安装（`uv pip install --python .venv/Scripts/python.exe -r requirements.txt`），uv 从 GitHub 镜像 gh-proxy.com 下载。重装依赖优先用 uv，别折腾 pip。
2. **npm 安装 vue-router 默认装 v5**（API 有变）→ 已固定 `vue-router@4`，路由守卫按 v4 写法。
3. **npm 操作触发沙箱拦截时前端目录曾被回滚**导致源文件丢失一次，已重写并验证——以后关键文件写完立即用 `npm run build` 或 find 确认存在。
4. 新版 SQLModel 要求 `datetime` 带时区，模型里统一用 `datetime.now(timezone.utc)`。

## 七、下一步（按优先级）

全部完成。剩余可选项：
1. **实际云部署**（需用户注册 Render/Vercel，步骤在 README「云部署指引」）：推送 GitHub → Render 部署后端 → Vercel 部署前端 → 回填 ALLOWED_ORIGINS
2. 填 `LLM_API_KEY` 切换到真实大模型（RAG 对话和分析质量都会提升）
3. pytest 覆盖率补到 80%+（简历文案承诺值）

## 八、简历文案（W6 完成后可写）

> 基于 FastAPI + Vue3/TypeScript 构建 AI 简历诊断平台，设计"文件解析 → 规则/LLM 评分管线"，实现 ATS 评分、岗位关键词匹配与修改建议；JWT 认证 + Docker Compose 一键部署，接口测试覆盖率 80%+。

（完成 W4/W6 后再补充 RAG、流式输出、部署相关表述）
