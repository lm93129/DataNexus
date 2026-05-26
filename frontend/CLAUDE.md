# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DataNexus 前端管理后台。Vue 3 + TypeScript + Naive UI 单页应用，通过 REST API 与 FastAPI 后端通信。

## Tech Stack

- Vue 3.5 (Composition API, `<script setup>`)
- TypeScript 6.0 (strict mode)
- Vite 8 (dev server + bundler)
- Naive UI 2.44 (组件库)
- Pinia 3 (状态管理)
- Vue Router 4 (路由，history mode)
- Axios (HTTP 客户端)
- Monaco Editor (SQL 编辑器)
- ECharts + vue-echarts (图表)
- pnpm (包管理器)

## Commands

```
pnpm install          # 安装依赖
pnpm dev              # 开发服务器 (localhost:3000)
pnpm build            # 类型检查 + 生产构建
npx vue-tsc --noEmit  # 仅类型检查
```

## Architecture

### API 层 (src/api/)

- `index.ts`: Axios 实例，baseURL="/api/v1"，自动注入 Bearer token，401 时跳转登录
- 各模块文件导出类型化的请求函数，返回值已经是 response.data（拦截器处理）
- 后端 API 前缀 /api/v1，Vite proxy 将 /api/* 转发到 http://localhost:8000

### 路由 (src/router/)

- `index.ts`: 路由定义，所有业务页面嵌套在 MainLayout 下
- `guard.ts`: 导航守卫，未登录重定向到 /login
- 路由 meta.requiresAuth 控制是否需要认证

### 状态管理 (src/stores/)

- `auth.ts`: token 存取（localStorage）、用户信息、角色判断
- 登录后 fetchUser() 获取 /auth/me 信息

### 视图 (src/views/)

每个功能模块一个目录：
- login/ — 登录页
- dashboard/ — 监控仪表盘（ECharts）
- datasource/ — 数据源 CRUD（列表 + 表单）
- metadata/ — 元数据浏览（树形 + 表格）
- query/ — SQL 查询（Monaco Editor + 结果表格 + CSV 导出）
- desensitize/ — 脱敏规则管理
- custom-api/ — 自定义 API 管理（低代码配置表单 + JSON 编辑器）
- audit/ — 审计日志查询
- settings/ — 系统设置（用户管理、修改密码、API Key）

### 布局 (src/layouts/)

- `MainLayout.vue`: 侧边栏导航 + 顶部栏 + 内容区
- 登录页使用 BlankLayout

## Key Patterns

**组件通信**: props + emit，v-model:value 双向绑定模式

**角色控制**: `useAuthStore().user?.role === 'admin'` 控制 UI 元素可见性（如用户管理 tab）

**表格操作列**: 使用 h() 渲染函数在 columns 定义中创建按钮

**表单验证**: Naive UI FormRules + FormInst.validate()

**低代码配置**: LowCodeConfigForm.vue 接收 v-model:value (LowCodeConfig 对象)，内部分6个 NCard 区域

**测试对话框**: TestParamsDialog.vue 根据 params 定义动态生成表单控件

## Path Aliases

`@/` → `src/` (tsconfig paths + vite resolve alias)

## Conventions

- 组件文件名 PascalCase，一个功能目录一个主组件
- API 函数命名: list*/get*/create*/update*/delete* + 资源名
- 中文 UI 文案直接写在模板中（无 i18n）
- 代码注释使用中文
