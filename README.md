<div align="center">

# 📊 DataNexus

**企业 AI 统一数据网关平台**

一套核心能力内核 · MCP + HTTP REST 双出口 · 一次配置、多端复用

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](#license)

<br/>

[快速开始](#-快速开始) · [技术架构](#-技术架构) · [API 概览](#-api-概览) · [MCP 配置](#-mcp-客户端配置) · [开发指南](#-开发指南) · [文档](#-文档)

</div>

---

## ✨ 项目简介

DataNexus 面向企业内部大模型、业务系统和自动化工具，提供统一的数据访问中枢。

| 出口 | 适用场景 | 协议 |
|:---:|---|---|
| 🤖 **MCP** | AI 模型获取元数据、执行安全查询、调用封装 API | MCP Protocol |
| 🌐 **REST** | 业务系统固定取数和系统集成 | HTTP REST API |
| 🖥️ **Console** | 管理员维护数据源、权限、脱敏规则、审计日志 | Vue 3 SPA |

**核心约束**

- 🔒 数据库访问**只读**，禁止 DML / DDL / 高风险 SQL
- 🛡️ 所有输出经过权限校验 → 风控 → 脱敏 → 审计
- ⚡ 双出口复用同一套服务层，零逻辑分叉
- 🚫 未授权默认拒绝，关键调用全链路可追溯
- 🔔 告警规则驱动通知（企业微信 / 钉钉 / 飞书 Webhook）

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     Client Layer                        │
│   🤖 AI Models        🌐 Business Systems    🖥️ Admin   │
└────────┬──────────────────┬──────────────────┬──────────┘
         │ MCP Protocol     │ HTTP REST        │ SPA
         ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                   DataNexus Gateway                     │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────────┐  │
│  │ MCP     │  │ REST API │  │ Auth / Rate-Limit /    │  │
│  │ Adapter │  │ Routes   │  │ Masking / Audit        │  │
│  └────┬────┘  └────┬─────┘  └──────────┬─────────────┘  │
│       └──────┬─────┘                   │                │
│         ┌────▼─────────────────────────▼──────────┐     │
│         │          Shared Service Layer            │     │
│         │  datasource · metadata · query · policy  │     │
│         └────────────────┬─────────────────────────┘     │
└──────────────────────────┼──────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         PostgreSQL    MySQL/SQLS    Oracle …
```

## 🚀 快速开始

### 方式一：Docker Compose 开发环境（推荐）

```bash
git clone https://github.com/lm93129/DataNexus.git
cd DataNexus
docker compose -f docker-compose.yml up -d --build
```

| 服务 | 地址 |
|---|---|
| 前端管理界面 | http://localhost:8088 |
| 后端 API | http://localhost:8000 |
| 健康检查 | http://localhost:8000/health |
| 本地 PostgreSQL | localhost:5432 |

开发环境会从本地 `backend/`、`frontend/` 构建镜像，并启动内置 PostgreSQL。

> **默认管理员** → `admin` / `admin123`

### 方式二：Docker Compose 生产环境

生产环境使用已发布到 Docker Hub 的镜像，不在目标机器上重新构建代码：

```bash
export DATANEXUS_DATABASE_URL="postgresql+asyncpg://user:password@host:5432/datanexus"
export DATANEXUS_SECRET_KEY="replace-with-a-random-secret"
export DATANEXUS_AES_KEY="replace-with-a-random-aes-key"

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

默认镜像为：

| 服务 | 镜像 |
|---|---|
| 后端 | `lm93129/datanexus-backend:latest` |
| 前端 | `lm93129/datanexus-frontend:latest` |

可通过以下变量覆盖镜像来源、版本和端口：

```bash
export DOCKERHUB_USERNAME="lm93129"
export DATANEXUS_IMAGE_TAG="latest"
export DATANEXUS_BACKEND_PORT="8000"
export DATANEXUS_FRONTEND_PORT="8088"
```

### 方式三：本地开发

<details>
<summary><b>后端</b></summary>

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

</details>

<details>
<summary><b>前端</b></summary>

```bash
cd frontend
pnpm install
pnpm dev
```

开发服务器启动后访问 http://localhost:3000，`/api` 请求自动代理到后端。

</details>

## 📦 技术栈

| 层级 | 技术 |
|---|---|
| **后端框架** | Python 3.11+, FastAPI, Uvicorn |
| **ORM / 迁移** | SQLAlchemy 2.0 (async), Alembic |
| **数据库** | PostgreSQL 16 (主库), MySQL / SQL Server / Oracle 11g+ (数据源) |
| **协议层** | MCP Python SDK, REST API |
| **前端框架** | Vue 3, TypeScript, Vite, Pinia, Naive UI |
| **前端能力** | Monaco Editor, ECharts, Axios |
| **本地编排** | Docker Compose |
| **Python 包管理** | [uv](https://docs.astral.sh/uv/) |
| **前端包管理** | pnpm |

## 🛠️ API 概览

### MCP 工具

| 工具 | 说明 |
|---|---|
| `list_datasources` | 列出当前用户可访问的数据源 |
| `get_database_schema` | 获取数据库元数据（表、字段、类型） |
| `query_database` | 执行安全只读 SQL 查询 |
| `call_custom_api` | 调用平台封装的内部 API |

### REST 端点

<details>
<summary>展开完整端点列表</summary>

| 方法 | 路径 | 说明 |
|:---:|---|---|
| `GET` | `/health` | 健康检查（含数据库连通性） |
| | **认证** | |
| `POST` | `/api/v1/auth/login` | 用户登录 |
| `GET` | `/api/v1/auth/me` | 当前用户信息 |
| `POST` | `/api/v1/auth/api-key/generate` | 生成 API Key |
| `DELETE` | `/api/v1/auth/api-key` | 撤销 API Key |
| | **数据源** | |
| `GET` | `/api/v1/datasources` | 数据源列表 |
| `POST` | `/api/v1/datasources` | 创建数据源 |
| `GET` | `/api/v1/datasources/{id}` | 数据源详情 |
| `PUT` | `/api/v1/datasources/{id}` | 更新数据源 |
| `DELETE` | `/api/v1/datasources/{id}` | 删除数据源 |
| | **元数据** | |
| `GET` | `/api/v1/metadata/tables/{id}` | 获取表列表 |
| `GET` | `/api/v1/metadata/columns/{id}` | 获取字段列表 |
| `GET` | `/api/v1/metadata/search` | 搜索表名 / 列名 |
| | **查询** | |
| `POST` | `/api/v1/query/execute` | 执行 SQL 查询 |
| `GET` | `/api/v1/query/history` | 查询历史 |
| `POST` | `/api/v1/query/export` | 导出查询结果 CSV |
| | **治理** | |
| `GET` | `/api/v1/desensitize-rules` | 脱敏规则列表 |
| `GET` | `/api/v1/custom-apis` | 自定义 API 列表 |
| `GET` | `/api/v1/audit/logs` | 审计日志查询 |
| `GET` | `/api/v1/dashboard/stats` | 仪表盘统计 |
| | **告警与通知** | |
| `GET` | `/api/v1/alerts/rules` | 告警规则列表 |
| `POST` | `/api/v1/alerts/rules` | 创建告警规则 |
| `PUT` | `/api/v1/alerts/rules/{id}` | 更新告警规则 |
| `DELETE` | `/api/v1/alerts/rules/{id}` | 删除告警规则 |
| `GET` | `/api/v1/alerts/records` | 告警记录列表 |
| `GET` | `/api/v1/alerts/channels` | 通知渠道列表 |
| `POST` | `/api/v1/alerts/channels` | 创建通知渠道 |

</details>
## 🔌 MCP 客户端配置

DataNexus 通过 **SSE (Server-Sent Events)** 传输协议对外暴露 MCP 服务，支持任何兼容 MCP 协议的客户端连接。

### 连接信息

| 项目 | 值 |
|---|---|
| SSE 端点 | `http://<host>:8000/mcp/sse` |
| 消息端点 | `http://<host>:8000/mcp/messages/` |
| 传输协议 | SSE (Server-Sent Events) |
| 最大并发连接 | 5 |

### 认证方式

MCP 请求支持两种认证方式，通过 HTTP Header 传递：

| 方式 | Header | 说明 |
|---|---|---|
| **API Key**（推荐） | `X-API-Key: <your-key>` | 通过管理端生成，适合 MCP 客户端场景 |
| **Bearer Token** | `Authorization: Bearer <jwt>` | 通过登录接口获取，适合短期调试 |

### Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "datanexus": {
      "url": "http://localhost:8000/mcp/sse",
      "headers": {
        "X-API-Key": "<your-api-key>"
      }
    }
  }
}
```

> 💡 **获取 API Key**：登录管理端 → 系统设置 → 生成 API Key，或调用 `POST /api/v1/auth/api-key/generate`

### Cursor 配置

在 `.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "datanexus": {
      "url": "http://localhost:8000/mcp/sse",
      "headers": {
        "X-API-Key": "<your-api-key>"
      }
    }
  }
}
```

### 其他 MCP 客户端

任何支持 MCP SSE 传输的客户端均可接入，需配置：

```
Transport:  SSE
URL:        http://<host>:8000/mcp/sse
Headers:    X-API-Key: <your-api-key>
```

### 可用工具

连接成功后，客户端可调用以下 MCP 工具：

```json
[
  {
    "name": "list_datasources",
    "description": "列出当前用户可访问的数据源列表",
    "inputSchema": {
      "type": "object",
      "properties": {},
      "required": []
    }
  },
  {
    "name": "get_database_schema",
    "description": "获取数据库元数据：表名列表或指定表的字段结构",
    "inputSchema": {
      "type": "object",
      "properties": {
        "datasource_id": { "type": "integer", "description": "数据源 ID" },
        "table_name":    { "type": "string",  "description": "表名（可选）" }
      },
      "required": ["datasource_id"]
    }
  },
  {
    "name": "query_database",
    "description": "执行安全的只读 SQL 查询，仅支持 SELECT 语句",
    "inputSchema": {
      "type": "object",
      "properties": {
        "datasource_id": { "type": "integer", "description": "数据源 ID" },
        "sql":           { "type": "string",  "description": "SELECT 查询语句" }
      },
      "required": ["datasource_id", "sql"]
    }
  },
  {
    "name": "call_custom_api",
    "description": "调用平台已封装的内部业务系统 API",
    "inputSchema": {
      "type": "object",
      "properties": {
        "api_name": { "type": "string",  "description": "API 名称" },
        "params":   { "type": "object",  "description": "调用参数（可选）" }
      },
      "required": ["api_name"]
    }
  }
]
```

### 注意事项

- 🔒 所有 MCP 工具调用受权限控制，API Key 对应的用户角色决定可访问的工具
- 📝 每次工具调用自动记录审计日志
- ⚠️ `query_database` 仅允许 `SELECT` 语句，`INSERT` / `UPDATE` / `DELETE` / `DROP` 等会被拦截
- 🔗 MCP 与 REST 共用同一套服务层，权限、脱敏、审计行为完全一致


## 📂 项目结构

```
DataNexus/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── core/                # 配置、数据库连接、安全工具
│   │   ├── models/              # SQLAlchemy ORM 模型（含告警/通知）
│   │   ├── schemas/             # Pydantic 请求 / 响应 Schema
│   │   ├── services/            # 核心业务逻辑（双出口共用 + 告警通知）
│   │   ├── api/                 # HTTP REST 路由
│   │   ├── mcp/                 # MCP 协议出口
│   │   ├── datasource/          # 多数据源连接池
│   │   └── middleware/          # 限流、审计中间件
│   ├── tests/                   # pytest 测试套件
│   └── alembic/                 # 数据库迁移脚本
├── frontend/                    # Vue 3 管理端
│   └── src/
│       ├── api/                 # Axios 接口封装
│       ├── components/          # 通用组件
│       ├── layouts/             # 页面布局
│       ├── router/              # 路由 & 登录守卫
│       ├── stores/              # Pinia 状态管理
│       └── views/               # 页面视图
├── docker-compose.yml           # 开发环境编排（本地构建 + 内置 PostgreSQL）
└── docker-compose.prod.yml      # 生产环境编排（Docker Hub 镜像）
```

## 🧪 开发指南

### 运行测试

```bash
cd backend && uv run pytest -v
```

### 代码质量检查

```bash
# 后端：编译检查 + 迁移一致性
cd backend
uv run python -m compileall app tests
uv run alembic heads

# 前端：类型检查 + 生产构建
cd frontend
pnpm build
```

### 环境变量

<details>
<summary>展开查看关键环境变量</summary>

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATANEXUS_DATABASE_URL` | PostgreSQL 连接串 | — |
| `DATANEXUS_SECRET_KEY` | JWT 签名密钥 | **必须修改** |
| `DATANEXUS_AES_KEY` | AES 加密密钥 | **必须修改** |
| `DATANEXUS_DEBUG` | 调试模式 | `false` |
| `DATANEXUS_ORACLE_CLIENT_DIR` | Oracle Instant Client 路径（11g thick 模式） | — |

> ⚠️ 生产环境**必须**替换默认密钥，数据源账号应使用**只读权限**。

</details>


## 🔐 安全

- 🚫 **不要**将 `.env`、API Key、数据库密码或生产密钥提交到仓库
- 🔑 生产环境**必须**替换 `DATANEXUS_SECRET_KEY` 和 `DATANEXUS_AES_KEY`
- 📋 审计日志仅记录请求 / 响应摘要，不保存原始敏感数据
- 🔄 MCP 与 REST 出口保持权限、风控、脱敏和审计行为**完全一致**

## 📄 License

[MIT](LICENSE)

---

<div align="center">

**DataNexus** — 一次配置，多端复用

</div>
