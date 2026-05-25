<template>
  <n-space vertical :size="16">
    <n-space align="center">
      <n-select
        v-model:value="datasourceId"
        :options="dsOptions"
        placeholder="选择数据源"
        style="width: 240px"
      />
      <n-button type="primary" :loading="executing" :disabled="!datasourceId" @click="handleExecute">
        执行 (Ctrl+Enter)
      </n-button>
    </n-space>
    <n-card>
      <SqlEditor v-model:modelValue="sql" height="200px" @execute="handleExecute" />
    </n-card>
    <n-card v-if="result" title="查询结果">
      <template #header-extra>
        <n-text depth="3">{{ result.row_count }} 行 · {{ result.duration_ms }}ms</n-text>
      </template>
      <n-data-table
        :columns="resultColumns"
        :data="result.data"
        :max-height="400"
        size="small"
        striped
      />
    </n-card>
    <n-alert v-if="error" type="error" :title="error" />
  </n-space>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SqlEditor from '@/components/SqlEditor.vue'
import { executeQuery, type QueryResult } from '@/api/query'
import { listDatasources } from '@/api/datasource'

const datasourceId = ref<number | null>(null)
const dsOptions = ref<{ label: string; value: number }[]>([])
const sql = ref('SELECT 1')
const executing = ref(false)
const result = ref<QueryResult | null>(null)
const error = ref('')

const resultColumns = ref<{ title: string; key: string }[]>([])

async function handleExecute() {
  if (!datasourceId.value || !sql.value.trim()) return
  executing.value = true
  error.value = ''
  result.value = null
  try {
    const res = await executeQuery({ datasource_id: datasourceId.value, sql: sql.value })
    if (!res.success) {
      error.value = res.error || '查询执行失败'
      return
    }
    result.value = res
    resultColumns.value = (res.columns || []).map((c) => ({ title: c, key: c }))
  } catch (e: any) {
    error.value = e.response?.data?.detail || '查询执行失败'
  } finally {
    executing.value = false
  }
}

onMounted(async () => {
  const list = await listDatasources()
  dsOptions.value = list.map((d) => ({ label: d.name, value: d.id }))
})
</script>
