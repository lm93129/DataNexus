<template>
  <n-layout has-sider>
    <n-layout-content style="padding: 16px">
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
          <n-button :disabled="!result || !result.success" @click="handleExport">导出 CSV</n-button>
          <n-button quaternary @click="showHistory = !showHistory">
            {{ showHistory ? '隐藏历史' : '查询历史' }}
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
        <!-- SQL 智能纠错建议 -->
        <n-card v-if="suggestions.length" title="智能纠错建议" size="small">
          <n-space vertical :size="8">
            <div v-for="(s, idx) in suggestions" :key="idx">
              <n-space align="center" :size="8">
                <n-tag :type="s.type === 'syntax' ? 'warning' : 'info'" size="small">
                  {{ s.type === 'syntax' ? '语法' : s.type === 'table' ? '表名' : '字段' }}
                </n-tag>
                <n-text>{{ s.message }}</n-text>
              </n-space>
              <n-space v-if="s.candidates && s.candidates.length" :size="8" style="margin-top: 4px; margin-left: 56px">
                <n-text depth="3" style="font-size: 12px">是否指:</n-text>
                <n-button
                  v-for="c in s.candidates"
                  :key="c"
                  size="tiny"
                  type="primary"
                  secondary
                  @click="applySuggestion(s, c)"
                >
                  {{ c }}
                </n-button>
              </n-space>
            </div>
          </n-space>
        </n-card>
      </n-space>
    </n-layout-content>

    <n-layout-sider
      v-if="showHistory"
      :width="320"
      bordered
      content-style="padding: 12px;"
      style="max-height: calc(100vh - 64px); overflow-y: auto"
    >
      <n-space vertical :size="8">
        <n-text strong>查询历史</n-text>
        <n-list v-if="history.length" hoverable clickable>
          <n-list-item v-for="item in history" :key="item.id" @click="replayHistory(item)">
            <template #prefix>
              <n-tag :type="item.status === 'success' ? 'success' : 'error'" size="small">
                {{ item.status === 'success' ? '成功' : '失败' }}
              </n-tag>
            </template>
            <template #suffix>
              <n-button text size="small" type="error" @click.stop="handleDeleteHistory(item.id)">删除</n-button>
            </template>
            <n-ellipsis :line-clamp="2" style="font-size: 12px; font-family: monospace">
              {{ item.sql }}
            </n-ellipsis>
            <n-text depth="3" style="font-size: 11px">
              {{ formatTime(item.created_at) }}
              <span v-if="item.duration_ms"> · {{ item.duration_ms }}ms</span>
              <span v-if="item.row_count !== null"> · {{ item.row_count }}行</span>
            </n-text>
          </n-list-item>
        </n-list>
        <n-empty v-else description="暂无历史记录" />
      </n-space>
    </n-layout-sider>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import SqlEditor from '@/components/SqlEditor.vue'
import { executeQuery, getQueryHistory, deleteQueryHistory, exportQueryCsv, type QueryResult, type QueryHistoryItem, type SqlSuggestion } from '@/api/query'
import { listDatasources } from '@/api/datasource'

const message = useMessage()

const datasourceId = ref<number | null>(null)
const dsOptions = ref<{ label: string; value: number }[]>([])
const sql = ref('SELECT 1')
const executing = ref(false)
const result = ref<QueryResult | null>(null)
const error = ref('')
const suggestions = ref<SqlSuggestion[]>([])
const showHistory = ref(false)
const history = ref<QueryHistoryItem[]>([])

const resultColumns = ref<{ title: string; key: string }[]>([])

async function handleExecute() {
  if (!datasourceId.value || !sql.value.trim()) return
  executing.value = true
  error.value = ''
  result.value = null
  suggestions.value = []
  try {
    const res = await executeQuery({ datasource_id: datasourceId.value, sql: sql.value })
    if (!res.success) {
      error.value = res.error || '查询执行失败'
      if (res.suggestions && res.suggestions.length) {
        suggestions.value = res.suggestions
      }
      return
    }
    result.value = res
    resultColumns.value = (res.columns || []).map((c) => ({ title: c, key: c }))
    await loadHistory()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '查询执行失败'
  } finally {
    executing.value = false
  }
}

async function handleExport() {
  if (!datasourceId.value || !sql.value.trim()) return
  try {
    const blob = await exportQueryCsv({ datasource_id: datasourceId.value, sql: sql.value })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'query_result.csv'
    a.click()
    URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch {
    message.error('导出失败')
  }
}

function applySuggestion(s: SqlSuggestion, candidate: string) {
  if (s.original) {
    // 替换 SQL 中的错误名称为建议的正确名称
    const regex = new RegExp(`\\b${s.original}\\b`, 'gi')
    sql.value = sql.value.replace(regex, candidate)
    message.info(`已替换 "${s.original}" → "${candidate}"`)
  }
}

async function loadHistory() {
  try {
    history.value = await getQueryHistory()
  } catch { /* ignore */ }
}

function replayHistory(item: QueryHistoryItem) {
  datasourceId.value = item.datasource_id
  sql.value = item.sql
}

async function handleDeleteHistory(id: number) {
  await deleteQueryHistory(id)
  history.value = history.value.filter((h) => h.id !== id)
}

function formatTime(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

onMounted(async () => {
  const list = await listDatasources()
  dsOptions.value = list.map((d) => ({ label: d.name, value: d.id }))
  await loadHistory()
})
</script>
