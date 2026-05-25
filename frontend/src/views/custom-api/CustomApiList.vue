<template>
  <n-space vertical :size="16">
    <n-card title="自定义 API 管理">
      <template #header-extra>
        <n-button type="primary" @click="handleCreate">新建 API</n-button>
      </template>
      <n-data-table :columns="tableColumns" :data="apis" size="small" />
    </n-card>

    <!-- 新建/编辑抽屉 -->
    <n-drawer v-model:show="showDrawer" :width="500" placement="right">
      <n-drawer-content :title="editingApi ? '编辑 API' : '新建 API'">
        <n-form :model="formData" label-placement="left" label-width="90">
          <n-form-item label="名称">
            <n-input v-model:value="formData.name" placeholder="API 名称" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input v-model:value="formData.description" type="textarea" placeholder="可选描述" :rows="2" />
          </n-form-item>
          <n-form-item label="模式">
            <n-radio-group v-model:value="formData.mode">
              <n-radio value="custom">自定义</n-radio>
              <n-radio value="low_code">低代码</n-radio>
            </n-radio-group>
          </n-form-item>
          <n-form-item label="配置 JSON">
            <n-input v-model:value="formData.config_json" type="textarea" placeholder='{"url":"...","method":"GET","headers":{}}' :rows="6" font="monospace" />
          </n-form-item>
          <n-form-item label="启用">
            <n-switch v-model:value="formData.is_active" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space>
            <n-button @click="showDrawer = false">取消</n-button>
            <n-button type="primary" @click="handleSave">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </n-space>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSwitch, useMessage, useDialog } from 'naive-ui'
import {
  listCustomApis,
  createCustomApi,
  updateCustomApi,
  deleteCustomApi,
  testCustomApi,
  type CustomApi,
} from '@/api/custom_api'

const message = useMessage()
const dialog = useDialog()

const apis = ref<CustomApi[]>([])
const showDrawer = ref(false)
const editingApi = ref<CustomApi | null>(null)
const formData = ref({
  name: '',
  description: '',
  mode: 'custom',
  config_json: '{"url":"","method":"GET","headers":{}}',
  is_active: true,
})

const tableColumns = [
  { title: '名称', key: 'name' },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '模式',
    key: 'mode',
    render: (row: CustomApi) => h(NTag, { type: row.mode === 'custom' ? 'info' : 'warning', size: 'small' }, () => row.mode),
  },
  {
    title: '状态',
    key: 'is_active',
    render: (row: CustomApi) => h(NSwitch, {
      value: row.is_active,
      size: 'small',
      onUpdateValue: (val: boolean) => handleToggle(row, val),
    }),
  },
  { title: '版本', key: 'version', width: 60 },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row: CustomApi) => h('div', { style: 'display:flex;gap:8px' }, [
      h(NButton, { size: 'small', onClick: () => handleEdit(row) }, () => '编辑'),
      h(NButton, { size: 'small', type: 'warning', onClick: () => handleTest(row) }, () => '测试'),
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, () => '删除'),
    ]),
  },
]

async function loadApis() {
  apis.value = await listCustomApis()
}

function handleCreate() {
  editingApi.value = null
  formData.value = { name: '', description: '', mode: 'custom', config_json: '{"url":"","method":"GET","headers":{}}', is_active: true }
  showDrawer.value = true
}

function handleEdit(api: CustomApi) {
  editingApi.value = api
  formData.value = {
    name: api.name,
    description: api.description || '',
    mode: api.mode,
    config_json: api.config_json,
    is_active: api.is_active,
  }
  showDrawer.value = true
}

async function handleSave() {
  try {
    JSON.parse(formData.value.config_json)
  } catch {
    message.error('配置 JSON 格式无效')
    return
  }
  try {
    if (editingApi.value) {
      await updateCustomApi(editingApi.value.id, formData.value)
      message.success('已更新')
    } else {
      await createCustomApi(formData.value)
      message.success('已创建')
    }
    showDrawer.value = false
    await loadApis()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleToggle(api: CustomApi, val: boolean) {
  await updateCustomApi(api.id, { is_active: val })
  await loadApis()
}

async function handleTest(api: CustomApi) {
  try {
    const res = await testCustomApi(api.id)
    if (res.success) {
      message.success(res.message)
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('测试请求失败')
  }
}

function handleDelete(api: CustomApi) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除 API "${api.name}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteCustomApi(api.id)
      message.success('已删除')
      await loadApis()
    },
  })
}

onMounted(loadApis)
</script>
