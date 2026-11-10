"""全局配置：从 .env 文件或环境变量读取。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # JWT 配置（生产环境务必修改 SECRET_KEY）
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # 数据库：默认 SQLite，部署时改为 PostgreSQL 连接串即可
    DATABASE_URL: str = "sqlite:///./resumepilot.db"

    # 允许跨域访问的前端地址（逗号分隔；生产环境必须改为实际前端域名）
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 可选：大模型 API Key。不配置则使用内置规则引擎分析
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_EMBED_MODEL: str = "text-embedding-3-small"


settings = Settings()
