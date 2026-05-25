<template>
  <n-space vertical :size="16">
    <n-card>
      <n-space>
        <n-select v-model:value="filters.action" :options="actionOptions" placeholder="操作类型" clearable style="width: 150px" />
        <n-button type="primary" @click="fetchData">查询</n-button>
      </n-space>
    </n-card>
    <n-data-table :columns="columns" :data="logs" :loading="loading" />
    <n-pagination
      v-model:page="pagination.page"
      :page-size="pagination.pageSize"
      :item-count="pagination.total"
      @update:page="fetchData"
    />
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag } from 'naive-ui'
import { getAuditLogs, type AuditLog } from '@/api/audit'

const logs = ref<AuditLog[]>([])
const loading = ref(false)

const filters = ref({ action: null as string | null })
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const actionOptions = [
  { label: '查询', value: 'query_database' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '登录', value: 'login' },
]

const statusTypeMap: Record<string, string> = {
  success: 'success',
  error: 'error',
}

const columns = [
  { title: '时间', key: 'created_at', width: 180 },
  {
    title: '操作',
    key: 'action',
    width: 120,
    render: (row: AuditLog) => {
      const typeMap: Record<string, string> = { query_database: 'info', create: 'success', update: 'warning', delete: 'error', login: 'default' }
      return h(NTag, { type: (typeMap[row.action] || 'default') as any, size: 'small' }, () => row.action)
    },
  },
  { title: '资源', key: 'resource', width: 200 },
  { title: '请求摘要', key: 'request_summary', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: (row: AuditLog) => h(NTag, { type: (statusTypeMap[row.status] || 'default') as any, size: 'small' }, () => row.status),
  },
  { title: '耗时(ms)', key: 'duration_ms', width: 90 },
  { title: 'IP', key: 'ip', width: 130 },
]

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
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
