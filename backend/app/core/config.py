from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DataNexus"
    debug: bool = False
    # SQL 明细日志会放大健康检查噪声，需要排查 SQL 时再显式启用。
    sql_echo: bool = False

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

    # Oracle Instant Client（thick 模式，支持 11g 等旧版本）
    oracle_client_dir: str | None = None
    oracle_connect_timeout_ms: int = 10000  # Oracle TCP 建连超时（毫秒）

    # CORS
    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_prefix": "DATANEXUS_"}


settings = Settings()
