<template>
  <n-space vertical :size="16">
    <n-card title="脱敏规则">
      <template #header-extra>
        <n-button type="primary" @click="showCreateModal = true">新建规则</n-button>
      </template>
      <n-data-table :columns="ruleColumns" :data="rules" size="small" />
    </n-card>

    <n-card title="列规则分配">
      <n-space align="center" :size="12" style="margin-bottom: 12px">
        <n-select
          v-model:value="selectedDs"
          :options="dsOptions"
          placeholder="选择数据源"
          style="width: 200px"
          @update:value="handleDsChange"
        />
        <n-select
          v-model:value="selectedTable"
          :options="tableOptions"
          placeholder="选择表"
          style="width: 200px"
          :disabled="!selectedDs"
          @update:value="handleTableChange"
        />
      </n-space>
      <n-data-table
        v-if="columns.length"
        :columns="colColumns"
        :data="columns"
        size="small"
      />
      <n-empty v-else description="请选择数据源和表" />
    </n-card>

    <!-- 新建/编辑规则弹窗 -->
    <n-modal v-model:show="showCreateModal" preset="dialog" :title="editingRule ? '编辑规则' : '新建规则'" positive-text="保存" negative-text="取消" @positive-click="handleSaveRule" @negative-click="showCreateModal = false">
      <n-form ref="formRef" :model="formData" label-placement="left" label-width="80">
        <n-form-item label="名称" path="name">
          <n-input v-model:value="formData.name" placeholder="规则名称（英文）" />
        </n-form-item>
        <n-form-item label="匹配模式" path="pattern">
          <n-input v-model:value="formData.pattern" placeholder="正则表达式" />
        </n-form-item>
        <n-form-item label="脱敏策略" path="mask_strategy">
          <n-input v-model:value="formData.mask_strategy" placeholder="如 regex_replace" />
        </n-form-item>
        <n-form-item label="替换值" path="replacement">
          <n-input v-model:value="formData.replacement" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSelect, useMessage, useDialog } from 'naive-ui'
import { listRules, createRule, updateRule, deleteRule, assignColumnRule, type DesensitizeRule } from '@/api/desensitize'
import { listDatasources } from '@/api/datasource'
import { getTables, getColumns, type ColumnMeta } from '@/api/metadata'

const message = useMessage()
const dialog = useDialog()

const rules = ref<DesensitizeRule[]>([])
const showCreateModal = ref(false)
const editingRule = ref<DesensitizeRule | null>(null)
const formData = ref({ name: '', pattern: '', mask_strategy: '', replacement: '' })

// 列规则分配
const selectedDs = ref<number | null>(null)
const dsOptions = ref<{ label: string; value: number }[]>([])
const selectedTable = ref<number | null>(null)
const tableOptions = ref<{ label: string; value: number }[]>([])
const columns = ref<ColumnMeta[]>([])

const ruleNameOptions = ref<{ label: string; value: string }[]>([])

const ruleColumns = [
  { title: '名称', key: 'name' },
  { title: '匹配模式', key: 'pattern' },
  { title: '脱敏策略', key: 'mask_strategy' },
  {
    title: '类型',
    key: 'is_builtin',
    render: (row: DesensitizeRule) => h(NTag, { type: row.is_builtin ? 'info' : 'success', size: 'small' }, () => row.is_builtin ? '内置' : '自定义'),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: DesensitizeRule) => {
      if (row.is_builtin) return ''
      return h('div', { style: 'display:flex;gap:8px' }, [
        h(NButton, { size: 'small', onClick: () => handleEdit(row) }, () => '编辑'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, () => '删除'),
      ])
    },
  },
]

const colColumns = [
  { title: '列名', key: 'column_name' },
  { title: '类型', key: 'data_type' },
  {
    title: '脱敏规则',
    key: 'desensitize_rule',
    render: (row: ColumnMeta) => h(NSelect, {
      value: row.desensitize_rule || null,
      options: [{ label: '无', value: null as any }, ...ruleNameOptions.value],
      size: 'small',
      clearable: true,
      style: 'width: 160px',
      onUpdateValue: (val: string | null) => handleAssign(row.id, val),
    }),
  },
]

async function loadRules() {
  rules.value = await listRules()
  ruleNameOptions.value = rules.value.map(r => ({ label: r.name, value: r.name }))
}

function handleEdit(rule: DesensitizeRule) {
  editingRule.value = rule
  formData.value = { name: rule.name, pattern: rule.pattern, mask_strategy: rule.mask_strategy, replacement: rule.replacement || '' }
  showCreateModal.value = true
}

function handleDelete(rule: DesensitizeRule) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除规则 "${rule.name}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteRule(rule.id!)
      message.success('已删除')
      await loadRules()
    },
  })
}

async function handleSaveRule() {
  const data = { ...formData.value, replacement: formData.value.replacement || undefined }
  if (editingRule.value) {
    await updateRule(editingRule.value.id!, data)
    message.success('已更新')
  } else {
    await createRule(data)
    message.success('已创建')
  }
  showCreateModal.value = false
  editingRule.value = null
  formData.value = { name: '', pattern: '', mask_strategy: '', replacement: '' }
  await loadRules()
  return true
}

async function handleDsChange(id: number) {
  selectedTable.value = null
  columns.value = []
  const tables = await getTables(id)
  tableOptions.value = tables.map(t => ({ label: t.table_name, value: t.id }))
}

async function handleTableChange(tableId: number) {
  columns.value = await getColumns(tableId)
}

async function handleAssign(columnId: number, ruleName: string | null) {
  await assignColumnRule(columnId, ruleName)
  message.success('规则已分配')
  if (selectedTable.value) {
    columns.value = await getColumns(selectedTable.value)
  }
}

onMounted(async () => {
  await loadRules()
  const list = await listDatasources()
  dsOptions.value = list.map(d => ({ label: d.name, value: d.id }))
})
</script>
