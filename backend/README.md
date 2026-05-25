# DataNexus 后端

企业AI统一数据网关平台后端服务，提供 MCP 协议 + HTTP REST API 双出口能力。

## 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy 2.0 (async) + PostgreSQL
- 官方 MCP Python SDK
- Pydantic V2

## 环境管理

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境和依赖。

### 初始化环境

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
```

### 运行服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 运行测试

```bash
uv run pytest -v
```

## 项目结构

```
backend/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── core/            # 核心配置（settings、数据库、安全）
│   ├── models/          # SQLAlchemy 数据模型
│   ├── schemas/         # Pydantic 请求/响应模型
│   ├── services/        # 核心业务逻辑（双出口共用）
│   ├── api/             # HTTP REST API 路由
│   ├── mcp/             # MCP 协议出口
│   ├── datasource/      # 多数据源连接池管理
│   └── middleware/      # 中间件（限流等）
├── tests/               # 测试
├── pyproject.toml       # 项目配置
└── Dockerfile
```

## API 端点

| 路径 | 说明 |
|------|------|
| GET /health | 健康检查 |
| POST /api/v1/auth/login | 用户登录 |
| GET /api/v1/datasources | 数据源列表 |
| POST /api/v1/datasources | 创建数据源 |
| GET /api/v1/metadata/tables/{id} | 获取表列表 |
| GET /api/v1/metadata/columns/{id} | 获取字段列表 |
| POST /api/v1/query/execute | 执行SQL查询 |
| GET /api/v1/audit/logs | 审计日志查询 |

## MCP 工具

| 工具名 | 说明 |
|--------|------|
| get_database_schema | 获取数据库元数据 |
| query_database | 安全SQL查询（仅SELECT） |
| call_custom_api | 调用封装的内部API |

## 环境变量

参考 `.env.example` 配置 `.env` 文件。
