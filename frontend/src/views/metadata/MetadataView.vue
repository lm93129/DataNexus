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
          <n-data-table
            :columns="tableColumns"
            :data="tables"
            :row-props="tableRowProps"
            size="small"
            :max-height="500"
          />
          <n-empty v-if="!tables.length" description="暂无数据" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card :title="selectedTableName ? `表结构: ${selectedTableName}` : '列信息'">
          <n-data-table v-if="columns.length" :columns="colColumns" :data="columns" size="small" :max-height="500" />
          <n-empty v-else description="请选择一张表" />
        </n-card>
      </n-gi>
    </n-grid>
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NInput, NButton, NSpace, useMessage } from 'naive-ui'
import { listDatasources } from '@/api/datasource'
import {
  getTables, getColumns, syncMetadata, searchMetadata,
  updateTableComment, updateColumnComment,
  type TableMeta, type ColumnMeta, type SearchResult,
} from '@/api/metadata'

const message = useMessage()
const selectedDs = ref<number | null>(null)
const dsOptions = ref<{ label: string; value: number }[]>([])
const tables = ref<TableMeta[]>([])
const selectedTableName = ref('')
const selectedTableId = ref<number | null>(null)
const columns = ref<ColumnMeta[]>([])
const syncing = ref(false)
const searchKeyword = ref('')
const searchResults = ref<SearchResult | null>(null)

// 内联编辑状态
const editingTableId = ref<number | null>(null)
const editingTableComment = ref('')
const editingColumnId = ref<number | null>(null)
const editingColumnComment = ref('')

// 表列表列定义（含可编辑注释）
const tableColumns = [
  { title: '表名', key: 'table_name', width: 180 },
  {
    title: '注释',
    key: 'table_comment',
    render: (row: TableMeta) => {
      if (editingTableId.value === row.id) {
        return h(NSpace, { size: 4, align: 'center' }, () => [
          h(NInput, {
            value: editingTableComment.value,
            size: 'small',
            placeholder: '输入注释',
            style: 'width: 140px',
            onUpdateValue: (v: string) => { editingTableComment.value = v },
            onKeyup: (e: KeyboardEvent) => { if (e.key === 'Enter') saveTableComment(row) },
          }),
          h(NButton, { size: 'tiny', type: 'primary', onClick: () => saveTableComment(row) }, () => '保存'),
          h(NButton, { size: 'tiny', onClick: () => { editingTableId.value = null } }, () => '取消'),
        ])
      }
      return h('span', {
        style: 'cursor: pointer; color: #666; min-width: 60px; display: inline-block',
        onClick: (e: Event) => { e.stopPropagation(); startEditTable(row) },
      }, row.table_comment || '点击编辑')
    },
  },
]

// 字段列定义（含可编辑注释）
const colColumns = [
  { title: '列名', key: 'column_name', width: 140 },
  { title: '类型', key: 'data_type', width: 100 },
  {
    title: '主键',
    key: 'is_primary_key',
    width: 60,
    render: (row: ColumnMeta) => row.is_primary_key ? h(NTag, { type: 'success', size: 'small' }, () => 'PK') : '',
  },
  {
    title: '注释',
    key: 'column_comment',
    render: (row: ColumnMeta) => {
      if (editingColumnId.value === row.id) {
        return h(NSpace, { size: 4, align: 'center' }, () => [
          h(NInput, {
            value: editingColumnComment.value,
            size: 'small',
            placeholder: '输入注释',
            style: 'width: 120px',
            onUpdateValue: (v: string) => { editingColumnComment.value = v },
            onKeyup: (e: KeyboardEvent) => { if (e.key === 'Enter') saveColumnComment(row) },
          }),
          h(NButton, { size: 'tiny', type: 'primary', onClick: () => saveColumnComment(row) }, () => '保存'),
          h(NButton, { size: 'tiny', onClick: () => { editingColumnId.value = null } }, () => '取消'),
        ])
      }
      return h('span', {
        style: 'cursor: pointer; color: #666; min-width: 60px; display: inline-block',
        onClick: () => startEditColumn(row),
      }, row.column_comment || '点击编辑')
    },
  },
]

function tableRowProps(row: TableMeta) {
  return {
    style: 'cursor: pointer',
    onClick: () => handleTableClick(row),
  }
}

function startEditTable(table: TableMeta) {
  editingTableId.value = table.id
  editingTableComment.value = table.table_comment || ''
}

async function saveTableComment(table: TableMeta) {
  try {
    await updateTableComment(table.id, editingTableComment.value)
    table.table_comment = editingTableComment.value
    editingTableId.value = null
    message.success('注释已更新')
  } catch {
    message.error('更新失败')
  }
}

function startEditColumn(col: ColumnMeta) {
  editingColumnId.value = col.id
  editingColumnComment.value = col.column_comment || ''
}

async function saveColumnComment(col: ColumnMeta) {
  try {
    await updateColumnComment(col.id, editingColumnComment.value)
    col.column_comment = editingColumnComment.value
    editingColumnId.value = null
    message.success('注释已更新')
  } catch {
    message.error('更新失败')
  }
}

async function handleDsChange(id: number) {
  selectedTableName.value = ''
  selectedTableId.value = null
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
  selectedTableId.value = table.id
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
