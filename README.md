# DataNexus

企业 AI 统一数据网关平台，面向企业内部大模型、业务系统和自动化工具提供统一的数据访问中枢。平台采用一套核心能力内核，对外提供 MCP 协议出口和 HTTP REST API 出口，统一承载数据源管理、元数据查询、安全 SQL 查询、权限控制、数据脱敏、审计日志和限流能力。

## 项目定位

DataNexus 的核心目标是让企业内部数据能力一次配置、多端复用：

- 面向 AI 模型：通过 MCP 工具获取数据库元数据、执行安全查询、调用封装 API。
- 面向业务系统：通过标准 HTTP REST API 进行固定取数和系统集成。
- 面向管理员：通过管理端维护数据源、权限、脱敏规则、审计日志和系统配置。

核心约束：

- 双出口只做协议适配，业务逻辑必须复用同一套服务层。
- 数据库访问必须只读，禁止 DML、DDL 和高风险 SQL。
- 所有对外数据输出必须经过权限校验、风控、脱敏和审计。
- 未授权默认拒绝，所有关键调用必须可追溯。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端 | Python, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Alembic |
| MCP | 官方 MCP Python SDK |
| 前端 | Vue 3, TypeScript, Vite, Naive UI, Pinia |
| 前端包管理 | pnpm |
| 本地服务 | Docker Compose |

## 目录结构

```text
DataNexus/
├── backend/                 # FastAPI 后端服务
│   ├── app/                 # 应用代码
│   ├── tests/               # 后端测试
│   ├── alembic/             # 数据库迁移
│   ├── pyproject.toml       # 后端依赖配置
│   └── README.md            # 后端说明
├── frontend/                # Vue 管理端
│   ├── src/                 # 前端源码
│   ├── package.json         # 前端脚本和依赖
│   └── vite.config.ts
├── docs/                    # 产品、设计、实施计划和审查清单
├── docker-compose.yml       # 本地 PostgreSQL + 后端开发环境
└── README.md                # 项目总览
```

## 快速开始

### 方式一：Docker Compose（推荐）

一键启动全部服务（PostgreSQL + 后端 + 前端）：

```bash
docker compose up -d
```

服务启动后：
- 前端管理界面：http://localhost
- 后端 API：http://localhost:8000
- 健康检查：http://localhost:8000/health
- 默认管理员：admin / admin123

### 方式二：本地开发

### 方式二：本地开发

**后端：**

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
pnpm install
pnpm dev
```

**运行测试：**

```bash
cd backend
uv run pytest -v
```

**构建前端：**

```bash
cd frontend
pnpm build
```

## 主要能力

### MCP 工具

| 工具名 | 说明 |
| --- | --- |
| `get_database_schema` | 获取数据库元数据 |
| `query_database` | 执行安全只读 SQL 查询 |
| `call_custom_api` | 调用平台封装的内部 API |

### HTTP API

| 路径 | 说明 |
| --- | --- |
| `GET /health` | 健康检查（含数据库连通性） |
| `POST /api/v1/auth/login` | 用户登录 |
| `GET /api/v1/auth/me` | 当前用户信息 |
| `POST /api/v1/auth/api-key/generate` | 生成 API Key |
| `DELETE /api/v1/auth/api-key` | 撤销 API Key |
| `GET /api/v1/datasources` | 数据源列表 |
| `POST /api/v1/datasources` | 创建数据源 |
| `GET /api/v1/metadata/tables/{id}` | 获取表列表 |
| `GET /api/v1/metadata/columns/{id}` | 获取字段列表 |
| `GET /api/v1/metadata/search` | 搜索表名/列名 |
| `POST /api/v1/query/execute` | 执行 SQL 查询 |
| `GET /api/v1/query/history` | 查询历史 |
| `POST /api/v1/query/export` | 导出查询结果 CSV |
| `GET /api/v1/desensitize-rules` | 脱敏规则列表 |
| `GET /api/v1/custom-apis` | 自定义 API 列表 |
| `GET /api/v1/audit/logs` | 审计日志查询 |
| `GET /api/v1/dashboard/stats` | 仪表盘统计 |

## 重要文档

- [产品 PRD](docs/企业AI统一数据网关平台（MCP+API双出口）产品PRD（AI开发专用版）.md)
- [技术选型设计](docs/superpowers/specs/2026-05-25-tech-stack-design.md)
- [后端实施计划](docs/superpowers/plans/2026-05-25-backend-implementation.md)
- [前端实施计划](docs/superpowers/plans/2026-05-25-frontend-implementation.md)
- [项目开发审查清单](docs/项目开发审查清单.md)
- [后端修复后检查清单](docs/后端修复后检查清单.md)
- [后端安全修复设计方案](docs/superpowers/specs/2026-05-25-backend-security-fixes-design.md)

## 开发检查

后端修复或阶段验收前，建议至少执行：

```bash
cd backend
uv run pytest -v
uv run python -m compileall app tests
uv run alembic heads
```

前端变更后，建议执行：

```bash
cd frontend
pnpm build
```

## 安全注意事项

- 不要将真实 `.env`、API Key、数据库密码或生产密钥提交到仓库。
- 生产环境必须替换默认 `DATANEXUS_SECRET_KEY` 和 `DATANEXUS_AES_KEY`。
- 数据源账号应使用只读权限。
- 审计日志只应记录请求和响应摘要，不应保存原始敏感数据。
- MCP 与 HTTP 出口必须保持权限、风控、脱敏和审计行为一致。
