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
    </n-space>
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
import { NTag } from 'naive-ui'
import { listDatasources } from '@/api/datasource'
import { getTables, getColumns, type TableMeta, type ColumnMeta } from '@/api/metadata'

const selectedDs = ref<number | null>(null)
const dsOptions = ref<{ label: string; value: number }[]>([])
const tables = ref<TableMeta[]>([])
const selectedTableName = ref('')
const columns = ref<ColumnMeta[]>([])

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
</script>
