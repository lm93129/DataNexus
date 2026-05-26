# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DataNexus 后端服务。FastAPI + SQLAlchemy 2.0 async，提供 HTTP REST API 和 MCP 协议双出口，共享业务逻辑层。

## Tech Stack

- Python 3.12+
- FastAPI (异步 Web 框架)
- SQLAlchemy 2.0 (async ORM, Mapped 类型注解)
- PostgreSQL (平台数据库，asyncpg 驱动)
- Pydantic v2 + pydantic-settings (配置 & 校验)
- python-jose (JWT)
- cryptography (Fernet 加密)
- httpx (异步 HTTP 客户端，用于自定义 API 调用)
- sqlglot (SQL AST 解析，风控)
- slowapi (限流)
- mcp (MCP 协议 SDK)

## Commands

```
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
.venv/Scripts/python -c "from app.main import app; print('OK')"  # 验证导入
```

虚拟环境位于 backend/.venv/，使用 .venv/Scripts/python.exe 执行。

## Architecture

### 目录结构

```
app/
├── main.py              # FastAPI 入口，lifespan 初始化默认管理员
├── core/
│   ├── config.py        # Pydantic Settings (DATANEXUS_ 前缀环境变量)
│   ├── database.py      # async_session_factory, engine
│   ├── security.py      # JWT, hash_password, verify_password, API key hash/encrypt/decrypt
│   └── permissions.py   # RBAC 权限矩阵 + require_permission() 依赖
├── models/              # SQLAlchemy ORM 模型
├── services/            # 业务逻辑层（HTTP 和 MCP 共用）
├── api/                 # HTTP REST 路由
│   ├── router.py        # 聚合所有子路由，前缀 /api/v1
│   ├── deps.py          # get_db, get_current_user 依赖
│   └── *.py             # 各资源路由模块
├── mcp/                 # MCP 协议
│   ├── server.py        # 工具定义 + 调用分发
│   ├── transport.py     # SSE 传输层
│   └── auth.py          # MCP 认证
├── datasource/
│   └── pool_manager.py  # 多数据源连接池管理
└── middleware/
    └── rate_limit.py    # 限流配置
```

### 请求流程

HTTP: Client → FastAPI route → require_permission() → Service → DB/外部API → Response
MCP:  Client → SSE → mcp_server.call_tool() → _dispatch_tool() → Service → Response

### 关键设计

**双出口共享**: services/ 层被 api/ 路由和 mcp/server.py 共同调用，确保行为一致。

**认证双通道**:
- JWT: Authorization: Bearer <token>，sub="user:<id>"
- API Key: X-API-Key header，PBKDF2 hash 验证 + Fernet 加密存储（可解密回显）

**RBAC**: 三角色 admin/analyst/viewer，权限格式 "resource:action"，通配符 "*"。
- admin: 全部权限
- analyst: query:execute, metadata:read, audit:read, datasource:read, desensitize:read, custom_api:read
- viewer: metadata:read

**SQL 风控**: SqlRiskControl 使用 sqlglot 解析 AST，阻止 DML/DDL，自动注入 LIMIT。

**数据源连接**: pool_manager 按 datasource_id 缓存 async engine，支持 MySQL/PostgreSQL/MSSQL/Oracle。密码 Fernet 加密存储。

**自定义 API 执行引擎**: 
- custom 模式: 简单 httpx 转发
- low_code 模式: _execute_low_code() 处理参数路由(path/query/body/header)、认证注入(bearer/basic/api_key)、body 模板、响应提取(JSONPath)

**SSRF 防护**: _is_ssrf_target() 阻止内网/本地地址访问。

## Configuration

环境变量前缀 DATANEXUS_，或 backend/.env 文件：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | 平台 PostgreSQL 连接串 | postgresql+asyncpg://postgres:postgres@localhost:5432/datanexus |
| SECRET_KEY | JWT 签名 + Fernet 密钥派生 | change-me-in-production |
| AES_KEY | 数据源密码加密 | change-me-16bytes |
| MAX_QUERY_ROWS | SQL 查询最大返回行数 | 1000 |
| DEBUG | 调试模式 | false |

## API Routes

所有路由前缀 /api/v1：

| 前缀 | 模块 | 说明 |
|------|------|------|
| /auth | user.py | 登录、/me、API Key 管理 |
| /users | user_mgmt.py | 用户 CRUD（admin） |
| /datasources | datasource.py | 数据源 CRUD + 连接测试 |
| /metadata | metadata.py | 元数据浏览（表/列） |
| /query | query.py | SQL 执行 + 历史 + CSV 导出 |
| /audit | audit.py | 审计日志查询 |
| /desensitize | desensitize.py | 脱敏规则 CRUD |
| /custom-apis | custom_api.py | 自定义 API CRUD + 测试 |
| /dashboard | dashboard.py | 仪表盘统计 |

MCP 端点: /mcp/sse (SSE stream), /mcp/messages/ (tool calls)

## Adding New Features

**新增 HTTP 接口**:
1. 在 models/ 添加 ORM 模型（如需）
2. 在 services/ 添加业务方法
3. 在 api/ 创建路由文件，使用 require_permission()
4. 在 api/router.py 注册子路由

**新增 MCP 工具**:
1. 在 mcp/server.py list_tools() 添加 Tool 定义
2. 实现 _handle_xxx() 函数（复用 services 层）
3. 在 _dispatch_tool() 添加分发 case

**修改权限**:
编辑 core/permissions.py 的 PERMISSION_MATRIX

## Conventions

- 异步优先：所有 DB 操作使用 async/await
- Service 层不直接抛 HTTPException，用 ValueError 或返回 None，由路由层转换
- 审计日志：所有写操作和敏感读操作记录到 AuditService
- 代码注释使用中文
