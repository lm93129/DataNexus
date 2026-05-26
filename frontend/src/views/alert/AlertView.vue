<template>
  <n-space vertical :size="24">
    <n-tabs type="line" default-value="records">
      <n-tab-pane name="records" tab="告警记录">
        <n-space vertical :size="16">
          <n-space align="center">
            <n-select
              v-model:value="filterStatus"
              :options="statusOptions"
              placeholder="筛选状态"
              clearable
              style="width: 160px"
              @update:value="loadRecords"
            />
            <n-text depth="3">共 {{ records.length }} 条</n-text>
          </n-space>
          <n-data-table :columns="recordColumns" :data="records" :loading="recordsLoading" :max-height="500" />
        </n-space>
      </n-tab-pane>
      <n-tab-pane name="rules" tab="告警规则">
        <n-space vertical :size="16">
          <n-space justify="end">
            <n-button type="primary" @click="openCreateRule">新增规则</n-button>
          </n-space>
          <n-data-table :columns="ruleColumns" :data="rules" :loading="rulesLoading" />
        </n-space>
      </n-tab-pane>
    </n-tabs>
  </n-space>

  <!-- 规则编辑弹窗 -->
  <n-modal v-model:show="showRuleModal" :title="editingRule ? '编辑告警规则' : '新增告警规则'" preset="dialog" style="width: 520px">
    <n-form :model="ruleForm">
      <n-form-item label="规则名称">
        <n-input v-model:value="ruleForm.name" placeholder="如：全局失败率告警" />
      </n-form-item>
      <n-form-item label="规则类型">
        <n-select v-model:value="ruleForm.rule_type" :options="ruleTypeOptions" @update:value="onRuleTypeChange" />
      </n-form-item>
      <!-- 动态阈值配置 -->
      <template v-if="ruleForm.rule_type === 'error_rate'">
        <n-form-item label="时间窗口（分钟）">
          <n-input-number v-model:value="ruleForm.threshold_config.window_minutes" :min="1" style="width: 100%" />
        </n-form-item>
        <n-form-item label="失败率阈值（%）">
          <n-input-number v-model:value="ruleForm.threshold_config.threshold_percent" :min="1" :max="100" style="width: 100%" />
        </n-form-item>
      </template>
      <template v-if="ruleForm.rule_type === 'high_frequency'">
        <n-form-item label="时间窗口（分钟）">
          <n-input-number v-model:value="ruleForm.threshold_config.window_minutes" :min="1" style="width: 100%" />
        </n-form-item>
        <n-form-item label="最大调用次数">
          <n-input-number v-model:value="ruleForm.threshold_config.max_calls" :min="1" style="width: 100%" />
        </n-form-item>
      </template>
      <template v-if="ruleForm.rule_type === 'slow_query'">
        <n-form-item label="耗时阈值（毫秒）">
          <n-input-number v-model:value="ruleForm.threshold_config.threshold_ms" :min="100" style="width: 100%" />
        </n-form-item>
      </template>
      <template v-if="ruleForm.rule_type === 'connection_fail'">
        <n-form-item label="连续失败次数">
          <n-input-number v-model:value="ruleForm.threshold_config.consecutive" :min="1" style="width: 100%" />
        </n-form-item>
      </template>
      <n-form-item label="作用范围">
        <n-select v-model:value="ruleForm.scope" :options="scopeOptions" />
      </n-form-item>
      <n-form-item v-if="ruleForm.scope !== 'global'" label="目标ID">
        <n-input-number v-model:value="ruleForm.target_id" :min="1" style="width: 100%" />
      </n-form-item>
      <n-form-item label="告警抑制（分钟）">
        <n-input-number v-model:value="ruleForm.suppress_minutes" :min="1" style="width: 100%" />
      </n-form-item>
    </n-form>
    <template #action>
      <n-button @click="showRuleModal = false">取消</n-button>
      <n-button type="primary" @click="handleSaveRule">保存</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NSpace, NSwitch, useMessage, useDialog } from 'naive-ui'
import {
  listAlertRules, createAlertRule, updateAlertRule, deleteAlertRule,
  listAlertRecords, acknowledgeAlert, resolveAlert,
  type AlertRule, type AlertRecord,
} from '@/api/alert'

const message = useMessage()
const dialog = useDialog()

const rules = ref<AlertRule[]>([])
const records = ref<AlertRecord[]>([])
const rulesLoading = ref(false)
const recordsLoading = ref(false)
const filterStatus = ref<string | null>(null)

const showRuleModal = ref(false)
const editingRule = ref<AlertRule | null>(null)
const ruleForm = ref(getDefaultForm())

function getDefaultForm() {
  return {
    name: '',
    rule_type: 'error_rate',
    threshold_config: { window_minutes: 5, threshold_percent: 50 } as Record<string, number>,
    scope: 'global',
    target_id: null as number | null,
    suppress_minutes: 10,
  }
}

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '已确认', value: 'acknowledged' },
  { label: '已解决', value: 'resolved' },
]

const ruleTypeOptions = [
  { label: '失败率超阈值', value: 'error_rate' },
  { label: '异常频次', value: 'high_frequency' },
  { label: '慢查询', value: 'slow_query' },
  { label: '连接失败', value: 'connection_fail' },
]

const scopeOptions = [
  { label: '全局', value: 'global' },
  { label: '按用户', value: 'user' },
  { label: '按数据源', value: 'datasource' },
]

const ruleTypeLabel: Record<string, string> = {
  error_rate: '失败率',
  high_frequency: '高频',
  slow_query: '慢查询',
  connection_fail: '连接失败',
}

const statusLabel: Record<string, string> = { pending: '待处理', acknowledged: '已确认', resolved: '已解决' }
const statusType: Record<string, string> = { pending: 'error', acknowledged: 'warning', resolved: 'success' }

function onRuleTypeChange(type: string) {
  if (type === 'error_rate') ruleForm.value.threshold_config = { window_minutes: 5, threshold_percent: 50 }
  else if (type === 'high_frequency') ruleForm.value.threshold_config = { window_minutes: 1, max_calls: 100 }
  else if (type === 'slow_query') ruleForm.value.threshold_config = { threshold_ms: 5000 }
  else if (type === 'connection_fail') ruleForm.value.threshold_config = { consecutive: 3 }
}

const ruleColumns = [
  { title: '规则名称', key: 'name' },
  { title: '类型', key: 'rule_type', width: 90, render: (row: AlertRule) => h(NTag, { size: 'small', type: 'info' }, () => ruleTypeLabel[row.rule_type] || row.rule_type) },
  { title: '范围', key: 'scope', width: 80 },
  { title: '抑制(分钟)', key: 'suppress_minutes', width: 100 },
  { title: '状态', key: 'is_active', width: 70, render: (row: AlertRule) => h(NSwitch, { value: row.is_active, onUpdateValue: (v: boolean) => handleToggleRule(row, v) }) },
  {
    title: '操作', key: 'actions', width: 140,
    render: (row: AlertRule) => h(NSpace, { size: 4 }, () => [
      h(NButton, { size: 'small', onClick: () => openEditRule(row) }, () => '编辑'),
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteRule(row) }, () => '删除'),
    ]),
  },
]

const recordColumns = [
  { title: '规则', key: 'rule_name', width: 140 },
  { title: '类型', key: 'rule_type', width: 80, render: (row: AlertRecord) => h(NTag, { size: 'small' }, () => ruleTypeLabel[row.rule_type] || row.rule_type) },
  { title: '详情', key: 'detail', ellipsis: { tooltip: true } },
  { title: '状态', key: 'status', width: 80, render: (row: AlertRecord) => h(NTag, { size: 'small', type: (statusType[row.status] || 'default') as any }, () => statusLabel[row.status] || row.status) },
  { title: '触发时间', key: 'triggered_at', width: 170, render: (row: AlertRecord) => row.triggered_at?.replace('T', ' ').slice(0, 19) },
  {
    title: '操作', key: 'actions', width: 160,
    render: (row: AlertRecord) => h(NSpace, { size: 4 }, () => {
      const btns: any[] = []
      if (row.status === 'pending') btns.push(h(NButton, { size: 'small', type: 'warning', onClick: () => handleAck(row) }, () => '确认'))
      if (row.status !== 'resolved') btns.push(h(NButton, { size: 'small', type: 'success', onClick: () => handleResolve(row) }, () => '解决'))
      return btns
    }),
  },
]

async function loadRules() {
  rulesLoading.value = true
  try { rules.value = await listAlertRules() } catch { /* ignore */ } finally { rulesLoading.value = false }
}

async function loadRecords() {
  recordsLoading.value = true
  try { records.value = await listAlertRecords(filterStatus.value || undefined) } catch { /* ignore */ } finally { recordsLoading.value = false }
}

function openCreateRule() {
  editingRule.value = null
  ruleForm.value = getDefaultForm()
  showRuleModal.value = true
}

function openEditRule(row: AlertRule) {
  editingRule.value = row
  ruleForm.value = {
    name: row.name,
    rule_type: row.rule_type,
    threshold_config: { ...row.threshold_config },
    scope: row.scope,
    target_id: row.target_id,
    suppress_minutes: row.suppress_minutes,
  }
  showRuleModal.value = true
}

async function handleSaveRule() {
  if (!ruleForm.value.name) { message.warning('请输入规则名称'); return }
  try {
    if (editingRule.value) {
      await updateAlertRule(editingRule.value.id, ruleForm.value as any)
      message.success('更新成功')
    } else {
      await createAlertRule(ruleForm.value as any)
      message.success('创建成功')
    }
    showRuleModal.value = false
    loadRules()
  } catch (e: any) { message.error(e.response?.data?.detail || '操作失败') }
}

async function handleToggleRule(row: AlertRule, active: boolean) {
  try {
    await updateAlertRule(row.id, { is_active: active } as any)
    row.is_active = active
  } catch { message.error('切换失败') }
}

function handleDeleteRule(row: AlertRule) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除告警规则「${row.name}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteAlertRule(row.id)
      message.success('删除成功')
      loadRules()
    },
  })
}

async function handleAck(row: AlertRecord) {
  try {
    await acknowledgeAlert(row.id)
    row.status = 'acknowledged'
    message.success('已确认')
  } catch { message.error('操作失败') }
}

async function handleResolve(row: AlertRecord) {
  try {
    await resolveAlert(row.id)
    row.status = 'resolved'
    message.success('已解决')
  } catch { message.error('操作失败') }
}

onMounted(() => {
  loadRules()
  loadRecords()
})
</script>
