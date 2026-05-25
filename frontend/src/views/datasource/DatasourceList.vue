<template>
  <n-space vertical :size="16">
    <n-space justify="space-between">
      <h2>数据源管理</h2>
      <n-button type="primary" @click="router.push('/datasource/create')">
        新增数据源
      </n-button>
    </n-space>
    <n-data-table :columns="columns" :data="datasources" :loading="loading" />
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSpace, NTag, useMessage, useDialog } from 'naive-ui'
import { listDatasources, deleteDatasource, testDatasourceConnection, type Datasource } from '@/api/datasource'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const datasources = ref<Datasource[]>([])
const loading = ref(false)

const columns = [
  { title: '名称', key: 'name' },
  { title: '类型', key: 'type', render: (row: Datasource) => h(NTag, { type: 'info' }, () => row.type.toUpperCase()) },
  { title: '主机', key: 'host' },
  { title: '端口', key: 'port' },
  { title: '数据库', key: 'database' },
  {
    title: '状态',
    key: 'is_active',
    render: (row: Datasource) => h(NTag, { type: row.is_active ? 'success' : 'default' }, () => row.is_active ? '启用' : '禁用'),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: Datasource) =>
      h(NSpace, null, () => [
        h(NButton, { size: 'small', type: 'info', onClick: () => handleTestConnection(row) }, () => '测试连接'),
        h(NButton, { size: 'small', onClick: () => router.push(`/datasource/${row.id}/edit`) }, () => '编辑'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, () => '删除'),
      ]),
  },
]

async function fetchData() {
  loading.value = true
  try {
    datasources.value = await listDatasources()
  } finally {
    loading.value = false
  }
}

async function handleTestConnection(row: Datasource) {
  try {
    const res = await testDatasourceConnection(row.id)
    if (res.success) {
      message.success(res.message)
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('测试连接失败')
  }
}

function handleDelete(row: Datasource) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除数据源「${row.name}」吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteDatasource(row.id)
      message.success('删除成功')
      fetchData()
    },
  })
}

onMounted(fetchData)
</script>
