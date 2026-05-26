from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DataNexus"
    debug: bool = False

    # 平台数据库
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/datanexus"

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # 安全
    aes_key: str = "change-me-16bytes"
    max_query_rows: int = 1000
    query_timeout_ms: int = 60000  # SQL 查询超时（毫秒）

    # CORS
    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_prefix": "DATANEXUS_"}


settings = Settings()
