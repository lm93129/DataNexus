<template>
  <n-space vertical :size="16">
    <n-card size="small">
      <n-space align="center" :wrap="true" :size="12">
        <n-input
          v-model:value="filters.username"
          placeholder="调用者"
          clearable
          style="width: 140px"
        />
        <n-select
          v-model:value="filters.action"
          :options="actionOptions"
          placeholder="操作类型"
          clearable
          style="width: 160px"
        />
        <n-input
          v-model:value="filters.resource"
          placeholder="资源（模糊）"
          clearable
          style="width: 160px"
        />
        <n-input
          v-model:value="filters.request_summary"
          placeholder="请求摘要（模糊）"
          clearable
          style="width: 180px"
        />
        <n-button type="primary" @click="handleSearch">查询</n-button>
        <n-button @click="handleReset">重置</n-button>
      </n-space>
    </n-card>

    <n-data-table
      :columns="columns"
      :data="logs"
      :loading="loading"
      :bordered="false"
      :single-line="false"
      size="small"
      striped
      :scroll-x="1100"
    />

    <n-space justify="end">
      <n-pagination
        v-model:page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :item-count="pagination.total"
        show-quick-jumper
        :page-sizes="[20, 50, 100]"
        show-size-picker
        @update:page="fetchData"
        @update:page-size="handlePageSizeChange"
      />
    </n-space>
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NSpace, NInput, useMessage } from 'naive-ui'
import { getAuditLogs, type AuditLog } from '@/api/audit'

const message = useMessage()
const logs = ref<AuditLog[]>([])
const loading = ref(false)

const filters = ref({
  action: null as string | null,
  resource: null as string | null,
  request_summary: null as string | null,
  username: null as string | null,
})
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const actionOptions = [
  { label: '查询数据库', value: 'query_database' },
  { label: '登录成功', value: 'login_success' },
  { label: '登录失败', value: 'login_failed' },
  { label: '账号禁用', value: 'login_disabled_account' },
  { label: '生成 API Key', value: 'generate_api_key' },
  { label: '撤销 API Key', value: 'revoke_api_key' },
  { label: '创建用户', value: 'user_create' },
  { label: '更新用户', value: 'user_update' },
  { label: '删除用户', value: 'user_delete' },
  { label: '创建数据源', value: 'datasource_create' },
  { label: '更新数据源', value: 'datasource_update' },
  { label: '删除数据源', value: 'datasource_delete' },
  { label: '测试数据源', value: 'datasource_test' },
  { label: '读取表列表', value: 'metadata_read_tables' },
  { label: '读取列信息', value: 'metadata_read_columns' },
  { label: '元数据搜索', value: 'metadata_search' },
  { label: '元数据同步', value: 'metadata_sync' },
  { label: '创建脱敏规则', value: 'desensitize_rule_create' },
  { label: '更新脱敏规则', value: 'desensitize_rule_update' },
  { label: '删除脱敏规则', value: 'desensitize_rule_delete' },
  { label: '分配脱敏规则', value: 'desensitize_assign' },
  { label: '创建自定义 API', value: 'custom_api_create' },
  { label: '更新自定义 API', value: 'custom_api_update' },
  { label: '删除自定义 API', value: 'custom_api_delete' },
  { label: 'MCP 查询', value: 'mcp_call:query_database' },
  { label: 'MCP 元数据', value: 'mcp_call:get_database_schema' },
  { label: 'MCP 列表', value: 'mcp_call:list_datasources' },
  { label: 'MCP 接口', value: 'mcp_call:call_custom_api' },
  { label: '权限拒绝', value: 'permission_denied' },
]

const identityTypeMap: Record<string, { label: string; type: string }> = {
  user: { label: '用户', type: 'info' },
  mcp_user: { label: 'MCP', type: 'success' },
  mcp_app: { label: 'MCP应用', type: 'warning' },
  mcp_model: { label: 'MCP模型', type: 'error' },
}

const actionTypeMap: Record<string, { label: string; type: string }> = {
  // 查询
  query_database: { label: '数据库查询', type: 'info' },
  // 认证
  login: { label: '登录', type: 'default' },
  login_success: { label: '登录成功', type: 'success' },
  login_failed: { label: '登录失败', type: 'error' },
  login_disabled_account: { label: '账号禁用', type: 'error' },
  generate_api_key: { label: '生成密钥', type: 'info' },
  revoke_api_key: { label: '撤销密钥', type: 'warning' },
  // 用户管理
  user_create: { label: '创建用户', type: 'success' },
  user_update: { label: '更新用户', type: 'warning' },
  user_delete: { label: '删除用户', type: 'error' },
  // 数据源
  datasource_create: { label: '创建数据源', type: 'success' },
  datasource_update: { label: '更新数据源', type: 'warning' },
  datasource_delete: { label: '删除数据源', type: 'error' },
  datasource_test: { label: '测试连接', type: 'info' },
  // 元数据
  metadata_read_tables: { label: '读取表', type: 'default' },
  metadata_read_columns: { label: '读取列', type: 'default' },
  metadata_search: { label: '元数据搜索', type: 'default' },
  metadata_sync: { label: '元数据同步', type: 'info' },
  // 脱敏规则
  desensitize_rule_create: { label: '创建脱敏规则', type: 'success' },
  desensitize_rule_update: { label: '更新脱敏规则', type: 'warning' },
  desensitize_rule_delete: { label: '删除脱敏规则', type: 'error' },
  desensitize_assign: { label: '分配脱敏规则', type: 'info' },
  // 自定义 API
  custom_api_create: { label: '创建接口', type: 'success' },
  custom_api_update: { label: '更新接口', type: 'warning' },
  custom_api_delete: { label: '删除接口', type: 'error' },
  // MCP 调用
  'mcp_call:query_database': { label: 'MCP查询', type: 'info' },
  'mcp_call:list_datasources': { label: 'MCP列表', type: 'default' },
  'mcp_call:get_database_schema': { label: 'MCP元数据', type: 'default' },
  'mcp_call:call_custom_api': { label: 'MCP接口', type: 'info' },
  // 权限
  permission_denied: { label: '权限拒绝', type: 'error' },
}

const columns = [
  {
    title: '时间',
    key: 'created_at',
    width: 170,
    render: (row: AuditLog) => {
      if (!row.created_at) return '-'
      const d = new Date(row.created_at)
      if (isNaN(d.getTime())) return row.created_at
      return d.toLocaleString('zh-CN', { hour12: false })
    },
  },
  {
    title: '调用者',
    key: 'username',
    width: 160,
    render: (row: AuditLog) => {
      const identity = identityTypeMap[row.identity_type] || { label: row.identity_type, type: 'default' }
      return h(NSpace, { align: 'center', size: 4, wrap: false }, () => [
        h('span', { style: 'font-weight: 500; white-space: nowrap;' }, row.username),
        h(NTag, { type: identity.type as any, size: 'tiny', round: true }, () => identity.label),
      ])
    },
  },
  {
    title: '操作',
    key: 'action',
    width: 100,
    render: (row: AuditLog) => {
      const action = actionTypeMap[row.action] || { label: row.action, type: 'default' }
      return h(NTag, { type: action.type as any, size: 'small' }, () => action.label)
    },
  },
  {
    title: '资源',
    key: 'resource',
    width: 180,
    ellipsis: { tooltip: true },
  },
  {
    title: '请求摘要',
    key: 'request_summary',
    minWidth: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'status',
    width: 80,
    align: 'center' as const,
    render: (row: AuditLog) => {
      const typeMap: Record<string, string> = { success: 'success', error: 'error', denied: 'warning' }
      return h(NTag, { type: (typeMap[row.status] || 'default') as any, size: 'small' }, () => row.status)
    },
  },
  {
    title: '耗时',
    key: 'duration_ms',
    width: 80,
    align: 'right' as const,
    render: (row: AuditLog) => {
      if (row.duration_ms == null) return '-'
      const color = row.duration_ms > 1000 ? '#d03050' : row.duration_ms > 500 ? '#f0a020' : ''
      return h('span', { style: color ? `color: ${color}; font-weight: 500;` : '' }, `${row.duration_ms}ms`)
    },
  },
  {
    title: 'IP',
    key: 'ip',
    width: 120,
  },
]

function handleSearch() {
  pagination.value.page = 1
  fetchData()
}

function handleReset() {
  filters.value = { action: null, resource: null, request_summary: null, username: null }
  pagination.value.page = 1
  fetchData()
}

function handlePageSizeChange(_pageSize: number) {
  pagination.value.page = 1
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    }
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.resource) params.resource = filters.value.resource
    if (filters.value.request_summary) params.request_summary = filters.value.request_summary
    if (filters.value.username) params.username = filters.value.username
    const res = await getAuditLogs(params)
    logs.value = res.items
    pagination.value.total = res.total
  } catch (e: any) {
    logs.value = []
    pagination.value.total = 0
    message.error(e?.response?.data?.detail || '获取审计日志失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
