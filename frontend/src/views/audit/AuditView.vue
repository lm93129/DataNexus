<template>
  <n-space vertical :size="16">
    <n-card size="small">
      <n-space align="center" :wrap="true" :size="12">
        <n-select
          v-model:value="filters.action"
          :options="actionOptions"
          placeholder="操作类型"
          clearable
          style="width: 160px"
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
import { NTag, NSpace, useMessage } from 'naive-ui'
import { getAuditLogs, type AuditLog } from '@/api/audit'

const message = useMessage()
const logs = ref<AuditLog[]>([])
const loading = ref(false)

const filters = ref({ action: null as string | null })
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const actionOptions = [
  { label: '查询数据库', value: 'query_database' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '登录成功', value: 'login_success' },
  { label: '登录失败', value: 'login_failed' },
  { label: '元数据同步', value: 'metadata_sync' },
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
  query_database: { label: '查询', type: 'info' },
  'mcp_call:query_database': { label: 'MCP查询', type: 'info' },
  'mcp_call:list_datasources': { label: 'MCP列表', type: 'default' },
  'mcp_call:get_database_schema': { label: 'MCP元数据', type: 'default' },
  'mcp_call:call_custom_api': { label: 'MCP接口', type: 'info' },
  create: { label: '创建', type: 'success' },
  update: { label: '更新', type: 'warning' },
  delete: { label: '删除', type: 'error' },
  login: { label: '登录', type: 'default' },
  login_success: { label: '登录', type: 'success' },
  login_failed: { label: '登录失败', type: 'error' },
  login_disabled_account: { label: '账号禁用', type: 'error' },
  metadata_sync: { label: '元数据同步', type: 'info' },
  permission_denied: { label: '拒绝', type: 'error' },
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
  filters.value = { action: null }
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
