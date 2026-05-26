<template>
  <n-card title="限流策略管理">
    <template #header-extra>
      <n-button type="primary" @click="openCreateRule">新增规则</n-button>
    </template>
    <n-data-table :columns="rlColumns" :data="rlRules" :loading="rlLoading" />
  </n-card>

  <!-- 限流规则弹窗 -->
  <n-modal v-model:show="showRlModal" :title="editingRule ? '编辑限流规则' : '新增限流规则'" preset="dialog" style="width: 500px">
    <n-form :model="rlForm">
      <n-form-item label="规则名称">
        <n-input v-model:value="rlForm.name" placeholder="如：全局默认限流" />
      </n-form-item>
      <n-form-item label="作用范围">
        <n-select v-model:value="rlForm.scope" :options="scopeOptions" />
      </n-form-item>
      <n-form-item v-if="rlForm.scope !== 'global'" label="目标ID">
        <n-input-number v-model:value="rlForm.target_id" :min="1" placeholder="用户/数据源/API的ID" style="width: 100%" />
      </n-form-item>
      <n-form-item label="每分钟上限">
        <n-input-number v-model:value="rlForm.max_per_minute" :min="1" placeholder="留空不限制" style="width: 100%" clearable />
      </n-form-item>
      <n-form-item label="每小时上限">
        <n-input-number v-model:value="rlForm.max_per_hour" :min="1" placeholder="留空不限制" style="width: 100%" clearable />
      </n-form-item>
      <n-form-item label="每日上限">
        <n-input-number v-model:value="rlForm.max_per_day" :min="1" placeholder="留空不限制" style="width: 100%" clearable />
      </n-form-item>
      <n-form-item label="单次最大行数">
        <n-input-number v-model:value="rlForm.max_rows_per_query" :min="1" placeholder="留空不限制" style="width: 100%" clearable />
      </n-form-item>
    </n-form>
    <template #action>
      <n-button @click="showRlModal = false">取消</n-button>
      <n-button type="primary" @click="handleSaveRule">保存</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NSpace, NSwitch, useMessage, useDialog } from 'naive-ui'
import { listRateLimits, createRateLimit, updateRateLimit, deleteRateLimit, type RateLimitRule } from '@/api/rateLimit'

const message = useMessage()
const dialog = useDialog()

const rlRules = ref<RateLimitRule[]>([])
const rlLoading = ref(false)
const showRlModal = ref(false)
const editingRule = ref<RateLimitRule | null>(null)
const rlForm = ref({ name: '', scope: 'global', target_id: null as number | null, max_per_minute: null as number | null, max_per_hour: null as number | null, max_per_day: null as number | null, max_rows_per_query: null as number | null })

const scopeOptions = [
  { label: '全局', value: 'global' },
  { label: '按用户', value: 'user' },
  { label: '按数据源', value: 'datasource' },
  { label: '按API', value: 'api' },
]

const scopeLabel: Record<string, string> = { global: '全局', user: '用户', datasource: '数据源', api: 'API' }

const rlColumns = [
  { title: '规则名称', key: 'name' },
  { title: '范围', key: 'scope', width: 90, render: (row: RateLimitRule) => h(NTag, { size: 'small', type: row.scope === 'global' ? 'info' : 'warning' }, () => scopeLabel[row.scope] || row.scope) },
  { title: '目标ID', key: 'target_id', width: 80, render: (row: RateLimitRule) => row.target_id ?? '-' },
  { title: '每分钟', key: 'max_per_minute', width: 80, render: (row: RateLimitRule) => row.max_per_minute ?? '-' },
  { title: '每小时', key: 'max_per_hour', width: 80, render: (row: RateLimitRule) => row.max_per_hour ?? '-' },
  { title: '每日', key: 'max_per_day', width: 80, render: (row: RateLimitRule) => row.max_per_day ?? '-' },
  { title: '最大行数', key: 'max_rows_per_query', width: 90, render: (row: RateLimitRule) => row.max_rows_per_query ?? '-' },
  { title: '状态', key: 'is_active', width: 70, render: (row: RateLimitRule) => h(NSwitch, { value: row.is_active, onUpdateValue: (v: boolean) => handleToggleRule(row, v) }) },
  {
    title: '操作', key: 'actions', width: 140,
    render: (row: RateLimitRule) => h(NSpace, { size: 4 }, () => [
      h(NButton, { size: 'small', onClick: () => openEditRule(row) }, () => '编辑'),
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteRule(row) }, () => '删除'),
    ]),
  },
]

async function fetchRlRules() {
  rlLoading.value = true
  try { rlRules.value = await listRateLimits() } catch { /* ignore */ } finally { rlLoading.value = false }
}

function openCreateRule() {
  editingRule.value = null
  rlForm.value = { name: '', scope: 'global', target_id: null, max_per_minute: null, max_per_hour: null, max_per_day: null, max_rows_per_query: null }
  showRlModal.value = true
}

function openEditRule(row: RateLimitRule) {
  editingRule.value = row
  rlForm.value = { name: row.name, scope: row.scope, target_id: row.target_id, max_per_minute: row.max_per_minute, max_per_hour: row.max_per_hour, max_per_day: row.max_per_day, max_rows_per_query: row.max_rows_per_query }
  showRlModal.value = true
}

async function handleSaveRule() {
  if (!rlForm.value.name) { message.warning('请输入规则名称'); return }
  try {
    if (editingRule.value) {
      await updateRateLimit(editingRule.value.id, rlForm.value)
      message.success('更新成功')
    } else {
      await createRateLimit(rlForm.value)
      message.success('创建成功')
    }
    showRlModal.value = false
    fetchRlRules()
  } catch (e: any) { message.error(e.response?.data?.detail || '操作失败') }
}

async function handleToggleRule(row: RateLimitRule, active: boolean) {
  try {
    await updateRateLimit(row.id, { is_active: active })
    row.is_active = active
  } catch (e: any) { message.error('切换失败') }
}

function handleDeleteRule(row: RateLimitRule) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除限流规则「${row.name}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteRateLimit(row.id)
      message.success('删除成功')
      fetchRlRules()
    },
  })
}

onMounted(fetchRlRules)
</script>
