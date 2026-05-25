<template>
  <n-space vertical :size="16">
    <n-space>
      <n-select
        v-model:value="selectedDs"
        :options="dsOptions"
        placeholder="选择数据源"
        style="width: 240px"
        @update:value="handleDsChange"
      />
      <n-input
        v-model:value="searchKeyword"
        placeholder="搜索表名/列名..."
        clearable
        style="width: 240px"
        @keyup.enter="handleSearch"
      />
      <n-button @click="handleSearch" :disabled="!searchKeyword">搜索</n-button>
      <n-button
        type="primary"
        :loading="syncing"
        :disabled="!selectedDs"
        @click="handleSync"
      >
        同步元数据
      </n-button>
    </n-space>

    <!-- 搜索结果 -->
    <n-card v-if="searchResults" title="搜索结果">
      <template #header-extra>
        <n-button text @click="searchResults = null">关闭</n-button>
      </template>
      <n-space vertical :size="8">
        <n-text v-if="searchResults.tables.length" strong>表 ({{ searchResults.tables.length }})</n-text>
        <n-list v-if="searchResults.tables.length" hoverable size="small">
          <n-list-item v-for="t in searchResults.tables" :key="t.id">
            <n-thing :title="t.table_name" :description="t.table_comment || ''" />
          </n-list-item>
        </n-list>
        <n-text v-if="searchResults.columns.length" strong>列 ({{ searchResults.columns.length }})</n-text>
        <n-list v-if="searchResults.columns.length" hoverable size="small">
          <n-list-item v-for="c in searchResults.columns" :key="c.id">
            <n-thing :title="c.column_name" :description="`${c.data_type}${c.column_comment ? ' - ' + c.column_comment : ''}`" />
          </n-list-item>
        </n-list>
        <n-empty v-if="!searchResults.tables.length && !searchResults.columns.length" description="无匹配结果" />
      </n-space>
    </n-card>

    <n-grid :cols="2" :x-gap="16">
      <n-gi>
        <n-card title="表列表">
          <n-list hoverable clickable>
            <n-list-item
              v-for="table in tables"
              :key="table.id"
              @click="handleTableClick(table)"
            >
              <n-thing :title="table.table_name" :description="table.table_comment || ''" />
            </n-list-item>
          </n-list>
          <n-empty v-if="!tables.length" description="暂无数据" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card :title="selectedTableName ? `表结构: ${selectedTableName}` : '列信息'">
          <n-data-table v-if="columns.length" :columns="colColumns" :data="columns" size="small" />
          <n-empty v-else description="请选择一张表" />
        </n-card>
      </n-gi>
    </n-grid>
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, useMessage } from 'naive-ui'
import { listDatasources } from '@/api/datasource'
import { getTables, getColumns, syncMetadata, searchMetadata, type TableMeta, type ColumnMeta, type SearchResult } from '@/api/metadata'

const message = useMessage()
const selectedDs = ref<number | null>(null)
const dsOptions = ref<{ label: string; value: number }[]>([])
const tables = ref<TableMeta[]>([])
const selectedTableName = ref('')
const columns = ref<ColumnMeta[]>([])
const syncing = ref(false)
const searchKeyword = ref('')
const searchResults = ref<SearchResult | null>(null)

const colColumns = [
  { title: '列名', key: 'column_name' },
  { title: '类型', key: 'data_type' },
  {
    title: '主键',
    key: 'is_primary_key',
    render: (row: ColumnMeta) => row.is_primary_key ? h(NTag, { type: 'success', size: 'small' }, () => 'PK') : '',
  },
  { title: '备注', key: 'column_comment' },
]

async function handleDsChange(id: number) {
  selectedTableName.value = ''
  columns.value = []
  try {
    tables.value = await getTables(id)
  } catch {
    tables.value = []
  }
}

async function handleSync() {
  if (!selectedDs.value) return
  syncing.value = true
  try {
    const res = await syncMetadata(selectedDs.value)
    message.success(`同步完成，共 ${res.table_count} 张表`)
    tables.value = await getTables(selectedDs.value)
  } catch {
    message.error('同步失败')
  } finally {
    syncing.value = false
  }
}

async function handleTableClick(table: TableMeta) {
  selectedTableName.value = table.table_name
  try {
    columns.value = await getColumns(table.id)
  } catch {
    columns.value = []
  }
}

onMounted(async () => {
  const list = await listDatasources()
  dsOptions.value = list.map((d) => ({ label: d.name, value: d.id }))
})

async function handleSearch() {
  if (!searchKeyword.value.trim()) return
  try {
    searchResults.value = await searchMetadata(searchKeyword.value, selectedDs.value || undefined)
  } catch {
    message.error('搜索失败')
  }
}
</script>
