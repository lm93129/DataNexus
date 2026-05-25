<template>
  <n-space vertical :size="16">
    <!-- 基础配置 -->
    <n-card title="基础配置" size="small">
      <n-form-item label="请求地址">
        <n-input v-model:value="config.url" placeholder="https://api.example.com/users/{user_id}/orders" />
      </n-form-item>
      <n-grid :cols="2" :x-gap="12">
        <n-gi>
          <n-form-item label="请求方法">
            <n-select v-model:value="config.method" :options="methodOptions" />
          </n-form-item>
        </n-gi>
        <n-gi>
          <n-form-item label="超时(秒)">
            <n-input-number v-model:value="config.timeout" :min="1" :max="120" />
          </n-form-item>
        </n-gi>
      </n-grid>
    </n-card>

    <!-- 认证配置 -->
    <n-card title="认证配置" size="small">
      <n-form-item label="认证方式">
        <n-radio-group v-model:value="config.auth.type">
          <n-radio-button value="none">无认证</n-radio-button>
          <n-radio-button value="bearer">Bearer Token</n-radio-button>
          <n-radio-button value="basic">Basic Auth</n-radio-button>
          <n-radio-button value="api_key">API Key</n-radio-button>
        </n-radio-group>
      </n-form-item>
      <n-form-item v-if="config.auth.type === 'bearer'" label="Token">
        <n-input v-model:value="config.auth.config.token" type="password" show-password-on="click" placeholder="Bearer Token" />
      </n-form-item>
      <template v-if="config.auth.type === 'basic'">
        <n-form-item label="用户名">
          <n-input v-model:value="config.auth.config.username" placeholder="用户名" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="config.auth.config.password" type="password" show-password-on="click" placeholder="密码" />
        </n-form-item>
      </template>
      <template v-if="config.auth.type === 'api_key'">
        <n-form-item label="Header 名称">
          <n-input v-model:value="config.auth.config.header" placeholder="X-API-Key" />
        </n-form-item>
        <n-form-item label="Key 值">
          <n-input v-model:value="config.auth.config.value" type="password" show-password-on="click" placeholder="API Key 值" />
        </n-form-item>
      </template>
    </n-card>

<!-- PLACEHOLDER_REMAINING -->

    <!-- 请求头 -->
    <n-card title="自定义请求头" size="small">
      <n-space vertical :size="8">
        <n-space v-for="(_, idx) in headerList" :key="idx" :size="8" align="center">
          <n-input v-model:value="headerList[idx].key" placeholder="Header 名称" style="width: 180px" />
          <n-input v-model:value="headerList[idx].value" placeholder="Header 值" style="width: 220px" />
          <n-button text type="error" @click="headerList.splice(idx, 1)">删除</n-button>
        </n-space>
        <n-button dashed size="small" @click="headerList.push({ key: '', value: '' })">添加请求头</n-button>
      </n-space>
    </n-card>

    <!-- 参数定义 -->
    <n-card title="参数定义" size="small">
      <template #header-extra>
        <n-button size="small" type="primary" @click="addParam">添加参数</n-button>
      </template>
      <n-data-table :columns="paramColumns" :data="config.params" size="small" :max-height="300" />
      <n-text v-if="urlPlaceholders.length" depth="3" style="margin-top: 8px; display: block; font-size: 12px">
        URL 中检测到路径参数: {{ urlPlaceholders.join(', ') }}
      </n-text>
    </n-card>

    <!-- 请求体模板 -->
    <n-card v-if="hasBodyParams" title="请求体模板（可选）" size="small">
      <n-space vertical :size="8">
        <n-space align="center">
          <n-switch v-model:value="useBodyTemplate" />
          <n-text>使用自定义 Body 模板</n-text>
        </n-space>
        <n-input
          v-if="useBodyTemplate"
          v-model:value="bodyTemplateStr"
          type="textarea"
          :rows="4"
          font="monospace"
          placeholder='{"user": "{{user_id}}", "data": "{{payload}}"}'
        />
        <n-text v-if="!useBodyTemplate" depth="3" style="font-size: 12px">
          未启用模板时，所有 body 参数将自动合并为 JSON 对象。
        </n-text>
      </n-space>
    </n-card>

    <!-- 响应处理 -->
    <n-card title="响应处理" size="small">
      <n-form-item label="数据提取路径">
        <n-input v-model:value="config.response.extract" placeholder="data.items（留空返回完整响应）" />
      </n-form-item>
      <n-text depth="3" style="font-size: 12px">
        支持点号分隔和数组索引，如: data.items、results[0].name
      </n-text>
    </n-card>
<!-- PLACEHOLDER_SCRIPT -->
  </n-space>
</template>

<script setup lang="ts">
import { ref, computed, watch, h } from 'vue'
import { NInput, NSelect, NSwitch, NButton, NInputNumber } from 'naive-ui'

export interface LowCodeConfig {
  url: string
  method: string
  timeout: number
  auth: { type: string; config: Record<string, string> }
  headers: Record<string, string>
  params: ParamDef[]
  body_template: any
  response: { extract: string | null; format: string | null }
}

export interface ParamDef {
  name: string
  type: string
  required: boolean
  default: any
  description: string
  in: string
}

const props = defineProps<{ value: LowCodeConfig }>()
const emit = defineEmits<{ (e: 'update:value', val: LowCodeConfig): void }>()

const config = computed({
  get: () => props.value,
  set: (val) => emit('update:value', val),
})

const headerList = ref<{ key: string; value: string }[]>([])
const useBodyTemplate = ref(false)
const bodyTemplateStr = ref('')

// 初始化 headerList
watch(() => props.value.headers, (h) => {
  if (h && typeof h === 'object') {
    headerList.value = Object.entries(h).map(([key, value]) => ({ key, value }))
  }
}, { immediate: true })

// headerList 变化同步到 config.headers
watch(headerList, (list) => {
  const headers: Record<string, string> = {}
  for (const item of list) {
    if (item.key.trim()) headers[item.key.trim()] = item.value
  }
  config.value = { ...config.value, headers }
}, { deep: true })

// body_template 同步
watch(() => props.value.body_template, (tpl) => {
  if (tpl) {
    useBodyTemplate.value = true
    bodyTemplateStr.value = typeof tpl === 'string' ? tpl : JSON.stringify(tpl, null, 2)
  }
}, { immediate: true })

watch([useBodyTemplate, bodyTemplateStr], ([use, str]) => {
  if (!use) {
    config.value = { ...config.value, body_template: null }
  } else {
    try {
      config.value = { ...config.value, body_template: JSON.parse(str) }
    } catch {
      config.value = { ...config.value, body_template: str }
    }
  }
})

const methodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'PATCH', value: 'PATCH' },
]

const typeOptions = [
  { label: 'string', value: 'string' },
  { label: 'integer', value: 'integer' },
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
  { label: 'object', value: 'object' },
]

const inOptions = [
  { label: 'path', value: 'path' },
  { label: 'query', value: 'query' },
  { label: 'body', value: 'body' },
  { label: 'header', value: 'header' },
]

const urlPlaceholders = computed(() => {
  const matches = config.value.url.match(/\{(\w+)\}/g)
  return matches ? matches.map(m => m.slice(1, -1)) : []
})

const hasBodyParams = computed(() => config.value.params.some(p => p.in === 'body'))

function addParam() {
  config.value = {
    ...config.value,
    params: [...config.value.params, { name: '', type: 'string', required: false, default: null, description: '', in: 'query' }],
  }
}

function removeParam(idx: number) {
  const params = [...config.value.params]
  params.splice(idx, 1)
  config.value = { ...config.value, params }
}

const paramColumns = [
  {
    title: '参数名',
    key: 'name',
    width: 120,
    render: (row: ParamDef, idx: number) => h(NInput, {
      value: row.name,
      size: 'small',
      placeholder: '参数名',
      onUpdateValue: (v: string) => { config.value.params[idx].name = v },
    }),
  },
  {
    title: '类型',
    key: 'type',
    width: 100,
    render: (row: ParamDef, idx: number) => h(NSelect, {
      value: row.type,
      size: 'small',
      options: typeOptions,
      onUpdateValue: (v: string) => { config.value.params[idx].type = v },
    }),
  },
  {
    title: '位置',
    key: 'in',
    width: 100,
    render: (row: ParamDef, idx: number) => h(NSelect, {
      value: row.in,
      size: 'small',
      options: inOptions,
      onUpdateValue: (v: string) => { config.value.params[idx].in = v },
    }),
  },
  {
    title: '必填',
    key: 'required',
    width: 60,
    render: (row: ParamDef, idx: number) => h(NSwitch, {
      value: row.required,
      size: 'small',
      onUpdateValue: (v: boolean) => { config.value.params[idx].required = v },
    }),
  },
  {
    title: '默认值',
    key: 'default',
    width: 100,
    render: (row: ParamDef, idx: number) => h(NInput, {
      value: row.default ?? '',
      size: 'small',
      placeholder: '默认值',
      onUpdateValue: (v: string) => { config.value.params[idx].default = v || null },
    }),
  },
  {
    title: '描述',
    key: 'description',
    render: (row: ParamDef, idx: number) => h(NInput, {
      value: row.description,
      size: 'small',
      placeholder: '参数描述',
      onUpdateValue: (v: string) => { config.value.params[idx].description = v },
    }),
  },
  {
    title: '',
    key: 'actions',
    width: 50,
    render: (_row: ParamDef, idx: number) => h(NButton, {
      size: 'small',
      text: true,
      type: 'error',
      onClick: () => removeParam(idx),
    }, () => '删除'),
  },
]
</script>
