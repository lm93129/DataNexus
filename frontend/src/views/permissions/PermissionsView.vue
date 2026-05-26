<template>
  <n-card title="权限矩阵">
    <template #header-extra>
      <n-text depth="3">只读展示，角色权限由系统预定义</n-text>
    </template>
    <n-spin :show="loading">
      <n-data-table
        v-if="tableData.length"
        :columns="columns"
        :data="tableData"
        :bordered="true"
        :single-line="false"
        size="small"
      />
    </n-spin>
  </n-card>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag } from 'naive-ui'
import { getPermissionMatrix, type PermissionMatrix } from '@/api/permissions'

const loading = ref(false)
const columns = ref<any[]>([])
const tableData = ref<any[]>([])

const roleLabel: Record<string, string> = {
  admin: '管理员',
  analyst: '分析师',
  viewer: '查看者',
}

const resourceLabel: Record<string, string> = {
  alert: '告警管理',
  audit: '审计日志',
  custom_api: '自定义API',
  datasource: '数据源',
  desensitize: '脱敏规则',
  metadata: '元数据',
  query: 'SQL查询',
  user: '用户管理',
}

function getActions(matrix: PermissionMatrix, role: string, resource: string): string[] {
  const perms = matrix.matrix[role] || []
  const matched: string[] = []
  for (const perm of perms) {
    const [res, action] = perm.split(':', 2)
    if (res === resource) matched.push(action)
  }
  return matched
}

function renderCell(actions: string[]) {
  if (!actions.length) {
    return h(NTag, { type: 'default', size: 'small', bordered: false }, () => '无权限')
  }
  if (actions.includes('*')) {
    return h(NTag, { type: 'success', size: 'small' }, () => '全部权限')
  }
  return actions.map(a =>
    h(NTag, { type: 'info', size: 'small', style: 'margin: 2px' }, () => a)
  )
}

async function fetchMatrix() {
  loading.value = true
  try {
    const data = await getPermissionMatrix()
    // 构建列定义
    columns.value = [
      { title: '资源模块', key: 'resource', width: 140, render: (row: any) => resourceLabel[row.resource] || row.resource },
      ...data.roles.map(role => ({
        title: roleLabel[role] || role,
        key: role,
        render: (row: any) => renderCell(getActions(data, role, row.resource)),
      })),
    ]
    // 构建行数据
    tableData.value = data.resources.map(resource => ({ resource }))
  } finally {
    loading.value = false
  }
}

onMounted(fetchMatrix)
</script>
