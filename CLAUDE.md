# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

DataNexus 是企业级 AI 统一数据网关平台，提供双协议接口（MCP + HTTP REST API），实现对多数据源的安全、可审计数据访问。平台强制只读访问、权限管控、数据脱敏和全面审计日志。

**核心约束**：所有业务逻辑必须在 MCP 和 HTTP 出口之间共享——仅做协议适配，不允许逻辑重复。

## 架构

### 整体设计

前端（Vue 3 + TS）通过 HTTP REST API 与 FastAPI 后端通信。后端暴露共享服务层，同时供 HTTP 路由和 MCP 工具调用。所有数据访问经过 SQL 校验、脱敏和审计日志。多数据源连接池将查询路由到 MySQL、MSSQL、Oracle 或 PostgreSQL。平台数据库（PostgreSQL）存储用户、角色、数据源、元数据缓存、审计日志和配置。

### 后端结构

backend/app/ 包含：
- main.py：FastAPI 应用入口，lifespan 钩子初始化默认管理员
- core/：配置（Pydantic Settings）、数据库（async SQLAlchemy）、安全（JWT/API Key/哈希）、权限（RBAC 矩阵）
- models/：SQLAlchemy ORM（User, Role, Datasource, TableMetadata, ColumnMetadata, AuditLog, DesensitizeRule, QueryHistory, CustomApi）
- services/：共享业务逻辑（QueryService, MetadataService, DatasourceService, AuditService, CustomApiService, DataDesensitizer, SqlRiskControl）
- api/：HTTP REST 路由（router.py 聚合所有子路由：user, datasource, metadata, query, audit, desensitize, custom_api, user_mgmt）
- mcp/：MCP 服务定义（server.py 列出工具并分发调用）、SSE 传输层（transport.py）、认证（auth.py）
- datasource/：连接池管理器（pool_manager.py）多数据源路由
- middleware/：限流（rate_limit.py，基于用户身份，使用 slowapi）

### 前端结构

frontend/src/ 包含：
- main.ts：Vue 应用入口，Pinia Store 初始化，Naive UI 插件
- router/：路由定义（login, dashboard, datasource, metadata, query, audit, settings），认证守卫
- stores/：Pinia 状态管理（auth：token/用户状态，app：主题/全局状态）
- api/：Axios 实例及拦截器（Bearer token 注入、401 重定向），各模块端点（auth, datasource, metadata, query, audit, desensitize, custom_api, dashboard, user）
- views/：页面组件（LoginView, DashboardView, DatasourceList/Form, MetadataView, QueryView, AuditView, DesensitizeView, CustomApiList, SettingsView）
- layouts/：MainLayout（侧边栏 + 顶栏）、BlankLayout（登录页）
- components/：SqlEditor（Monaco 编辑器封装）
- utils/：Token 管理（localStorage）

### 关键设计模式

**认证双通道**：JWT（Bearer token，sub="user:<id>"）或 API Key（X-API-Key header）。均在数据库中哈希/验证。MCP 需在 SSE 流建立前完成认证。

**RBAC 授权**：三角色（admin/analyst/viewer）。权限矩阵在 core/permissions.py。路由使用 @require_permission("resource:action") 装饰器。

**SQL 风控**：SqlRiskControl 校验 SQL（阻止 DML/DDL），通过 sqlglot AST 自动注入行数限制。脱敏自动执行（模式匹配 + 自动检测）加列级规则。强制只读。

**审计日志**：集中式 AuditService 记录所有访问（HTTP 和 MCP）。字段：identity_id, identity_type, action, resource, status, duration_ms。MCP 当前使用占位 identity_id=0。

**共享服务层**：app/services/ 中的服务同时被 HTTP 路由和 MCP 工具调用。HTTP 路由直接调用；MCP 工具通过 _dispatch_tool → _handle_* 函数调用。确保行为一致。

**连接池管理**：按数据源缓存 async engine。凭证按需解密。支持 MySQL（aiomysql）、PostgreSQL（asyncpg）、MSSQL（aioodbc）、Oracle（oracledb）。

## 开发命令

### 后端

cd backend

环境搭建：python -m venv .venv && .venv/Scripts/pip install -e ".[all-drivers,dev]"
开发服务器：.venv/Scripts/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
导入验证：.venv/Scripts/python -c "from app.main import app; print('OK')"

### 前端

cd frontend

安装依赖：pnpm install
开发服务器：pnpm dev（http://localhost:3000，/api 代理到 http://localhost:8000/api/v1）
生产构建：pnpm build
类型检查：npx vue-tsc --noEmit

## 环境变量

后端（app/core/config.py，Pydantic Settings，DATANEXUS_ 前缀）：
DATANEXUS_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/datanexus
DATANEXUS_SECRET_KEY=change-me-in-production（用于 JWT 签名 + Fernet 密钥派生）
DATANEXUS_DEBUG=true
DATANEXUS_MAX_QUERY_ROWS=1000
DATANEXUS_ORACLE_CLIENT_DIR=D:\oracle\instantclient_19_x（Oracle 11g thick 模式需要，需 19c+ 客户端）

前端（vite.config.ts 代理配置）：
/api/* 请求代理到后端 http://localhost:8000/api/v1/*

## 常见开发任务

**新增 HTTP 接口**：创建 Pydantic schema（如需）→ 添加 service 方法 → 创建路由并使用 @require_permission() → 注册到 api/router.py → 前端 src/api/ 添加 API 调用 → 创建视图组件。

**新增 MCP 工具**：在 mcp/server.py list_tools() 添加 Tool 定义 → 实现 _handle_*() 函数 → 在 _dispatch_tool() 添加分发 case → 复用 service 层。

**自定义 API（low_code 模式）**：配置以结构化 JSON 存储（url, method, timeout, auth, headers, params[], body_template, response.extract）。执行引擎在 services/custom_api.py._execute_low_code()，处理参数路由（path/query/body/header）、认证注入和响应提取。

## 重要文件

- app/core/permissions.py：RBAC 权限矩阵，修改角色/权限在此
- app/services/custom_api.py：自定义 API 执行引擎（low_code + custom 模式）
- app/services/security.py：SQL 校验与脱敏逻辑
- app/datasource/pool_manager.py：多数据源路由，新增数据库类型在此
- app/mcp/server.py：MCP 工具定义和分发
- app/api/deps.py：认证依赖注入（get_current_user）
- app/core/security.py：JWT 创建/验证、API Key 哈希/加密、密码哈希
- frontend/src/router/index.ts：路由定义和认证守卫
- frontend/src/stores/auth.ts：认证状态管理（token, user, role）
- frontend/src/api/index.ts：Axios 实例及拦截器

## 测试

后端：通过 curl/httpx 对运行中的服务器进行手动测试
前端：浏览器手动测试（未配置测试框架）
集成测试：启动后端（端口 8000）+ 前端（端口 3000），前端代理 API 请求

## 安全说明

- 数据源密码使用 Fernet 加密（密钥由 sha256(SECRET_KEY) 派生）
- API Key 双重存储——PBKDF2 哈希（验证用）+ Fernet 加密（回显用）
- JWT token：sub="user:<id>"，24 小时过期
- 所有查询记录到审计表（identity_id, action, resource, status）
- 基于用户身份的限流（slowapi）
- SSRF 防护：阻止自定义 API 调用访问内网/本地地址
- MCP 和 HTTP 出口共享相同的权限/审计行为

## 已知限制

- MCP 上下文身份硬编码为 0，应从 SSE 认证上下文中提取
- 无自动化测试套件（手动浏览器 + curl 测试）
- SQL Server 数据源类型：前端使用 "sqlserver"，后端期望 "mssql"
