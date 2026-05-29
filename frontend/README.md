# DataNexus 前端管理后台

DataNexus 前端是企业 AI 统一数据网关平台的管理后台，提供数据源管理、元数据浏览、SQL 查询、审计日志、监控仪表盘和系统设置等基础页面。

## 技术栈

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Axios
- Naive UI
- ECharts / vue-echarts
- Monaco Editor
- pnpm

## 目录结构

```text
frontend/
├── public/                 # 静态资源
├── src/
│   ├── api/                # Axios 实例与接口封装
│   ├── assets/             # 全局样式与资源
│   ├── components/         # 通用组件
│   ├── layouts/            # 页面布局
│   ├── router/             # 路由与登录守卫
│   ├── stores/             # Pinia 状态
│   └── views/              # 页面视图
├── .env.development        # 本地开发环境变量
├── package.json
├── pnpm-lock.yaml
└── vite.config.ts
```

## 本地运行

### 环境要求

- Node.js LTS
- pnpm 10.x
- 后端服务默认运行在 `http://localhost:8000`

### 安装依赖

```bash
cd frontend
pnpm install
```

### 启动开发服务

```bash
pnpm dev
```

默认访问地址：

```text
http://localhost:3000
```

Vite 已配置 `/api` 代理到后端：

```text
/api -> http://localhost:8000
```

前端 Axios 默认请求前缀为：

```text
/api/v1
```

### 构建生产包

```bash
pnpm build
```

构建流程包含 TypeScript 类型检查：

```text
vue-tsc --noEmit && vite build
```

### 本地预览生产包

```bash
pnpm preview
```

## 环境变量

当前开发环境变量位于 `.env.development`：

```env
VITE_API_BASE_URL=/api/v1
```

默认值 `/api/v1` 会在开发环境通过 Vite proxy 转发到后端，在 Docker Compose 中通过 nginx 转发到 `backend:8000`。

如需连接其他浏览器可访问的后端地址，请使用完整 API 前缀，例如：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Docker 镜像构建时会读取同名构建参数；修改该变量后需要重新构建前端镜像。

## 页面与路由

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | 登录页 | 用户登录并写入 JWT Token |
| `/dashboard` | 监控仪表盘 | 展示数据源数量、查询量、活跃用户、错误率和趋势图 |
| `/datasource` | 数据源管理 | 数据源列表、新增、编辑、删除 |
| `/datasource/create` | 新增数据源 | 创建数据库连接配置 |
| `/datasource/:id/edit` | 编辑数据源 | 更新数据库连接配置 |
| `/metadata` | 元数据浏览 | 按数据源查看表和字段结构 |
| `/query` | SQL 查询 | 选择数据源并执行只读查询 |
| `/audit` | 审计日志 | 查看调用审计记录 |
| `/settings` | 系统设置 | 用户管理和修改密码入口 |

## 接口联调状态

### 已按当前后端契约对齐

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/datasources`
- `POST /api/v1/datasources`
- `GET /api/v1/datasources/{id}`
- `PUT /api/v1/datasources/{id}`
- `DELETE /api/v1/datasources/{id}`
- `GET /api/v1/metadata/tables/{datasource_id}`
- `GET /api/v1/metadata/columns/{table_metadata_id}`
- `POST /api/v1/query/execute`
- `GET /api/v1/audit/logs`

### 后端暂未就绪或需继续统一

- `GET /api/v1/dashboard/stats`
- `GET /api/v1/dashboard/query-trend`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PUT /api/v1/users/{id}`
- `DELETE /api/v1/users/{id}`
- `POST /api/v1/users/change-password`
- SQL Server 数据源类型值需统一：前端当前表单值为 `sqlserver`，后端驱动映射使用 `mssql`。

## 认证与请求

- Token 存储键：`datanexus_token`
- 请求拦截器会自动注入：

```text
Authorization: Bearer <token>
```

- 收到 `401` 响应后会清理 Token 并跳转 `/login`。
- 路由守卫会阻止未登录用户访问管理后台页面。

## 常用验证

```bash
cd frontend
pnpm build
```

可选检查前端接口调用：

```bash
rg -n "request\\.(get|post|put|delete|patch)" src/api src/views
```

浏览器联调时建议检查：

- Network 面板中是否存在非预期 `404`。
- Console 面板中是否存在 Vue 运行时错误。
- 登录后请求是否携带 `Authorization` 头。
- 查询失败时页面是否展示后端返回的错误信息。

## 已知注意事项

- Monaco Editor 会带来较大的构建产物，当前构建会出现大 chunk 警告；这不影响编译通过，但后续可按需拆包优化。
- 仪表盘和用户管理相关后端接口未就绪时，前端会以默认值或提示信息降级展示。
- PRD 中的自定义 API 编排、权限管理、脱敏规则和限流策略入口仍需后续补齐。
