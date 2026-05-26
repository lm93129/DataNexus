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
          <SqlEditor ref="editorRef" v-model:modelValue="sql" height="200px" @execute="handleExecute" />
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
import { MarkerSeverity } from 'monaco-editor'
import SqlEditor from '@/components/SqlEditor.vue'
import { executeQuery, getQueryHistory, deleteQueryHistory, exportQueryCsv, type QueryResult, type QueryHistoryItem, type SqlSuggestion } from '@/api/query'
import { listDatasources } from '@/api/datasource'

const message = useMessage()
const editorRef = ref<InstanceType<typeof SqlEditor> | null>(null)

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

// 将字符偏移量转换为行号和列号
function offsetToPosition(text: string, offset: number): { line: number; col: number } {
  let line = 1
  let col = 1
  for (let i = 0; i < offset && i < text.length; i++) {
    if (text[i] === '\n') {
      line++
      col = 1
    } else {
      col++
    }
  }
  return { line, col }
}

// 在 SQL 文本中查找标识符的位置（不区分大小写）
function findWordPosition(text: string, word: string): { line: number; col: number } | null {
  const regex = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i')
  const match = regex.exec(text)
  if (!match) return null
  return offsetToPosition(text, match.index)
}

// 根据 suggestions 生成 Monaco markers
function buildMarkers(sqlText: string, items: SqlSuggestion[]): import('monaco-editor').editor.IMarkerData[] {
  const markers: import('monaco-editor').editor.IMarkerData[] = []
  for (const s of items) {
    let startLine = 1
    let startCol = 1
    let endCol = startCol + 1

    if (s.type === 'syntax' && s.position != null) {
      // sqlglot position 是字符偏移量
      const pos = offsetToPosition(sqlText, s.position)
      startLine = pos.line
      startCol = pos.col
      // 标记到行尾或下一个空白
      const lineText = sqlText.split('\n')[startLine - 1] || ''
      const rest = lineText.substring(startCol - 1)
      const wordMatch = rest.match(/^\S+/)
      endCol = startCol + (wordMatch ? wordMatch[0].length : 1)
    } else if (s.original) {
      const pos = findWordPosition(sqlText, s.original)
      if (pos) {
        startLine = pos.line
        startCol = pos.col
        endCol = startCol + s.original.length
      }
    }

    let msg = s.message
    if (s.candidates && s.candidates.length) {
      msg += `\n建议: ${s.candidates.join(', ')}`
    }

    markers.push({
      severity: MarkerSeverity.Error,
      message: msg,
      startLineNumber: startLine,
      startColumn: startCol,
      endLineNumber: startLine,
      endColumn: endCol,
    })
  }
  return markers
}

async function handleExecute() {
  if (!datasourceId.value || !sql.value.trim()) return
  executing.value = true
  error.value = ''
  result.value = null
  suggestions.value = []
  editorRef.value?.clearMarkers()
  try {
    const res = await executeQuery({ datasource_id: datasourceId.value, sql: sql.value })
    if (!res.success) {
      error.value = res.error || '查询执行失败'
      if (res.suggestions && res.suggestions.length) {
        suggestions.value = res.suggestions
        // 设置 Monaco 错误标记
        const markers = buildMarkers(sql.value, res.suggestions)
        if (markers.length) {
          editorRef.value?.setMarkers(markers)
        }
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
