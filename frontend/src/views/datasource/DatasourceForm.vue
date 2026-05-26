<template>
  <n-card :title="isEdit ? '编辑数据源' : '新增数据源'">
    <n-form ref="formRef" :model="formData" :rules="rules" label-placement="left" label-width="80">
      <n-form-item label="名称" path="name">
        <n-input v-model:value="formData.name" placeholder="数据源名称" />
      </n-form-item>
      <n-form-item label="类型" path="type">
        <n-select v-model:value="formData.type" :options="typeOptions" placeholder="选择数据库类型" />
      </n-form-item>
      <n-form-item label="主机" path="host">
        <n-input v-model:value="formData.host" placeholder="主机地址" />
      </n-form-item>
      <n-form-item label="端口" path="port">
        <n-input-number v-model:value="formData.port" :min="1" :max="65535" />
      </n-form-item>
      <n-form-item label="数据库" path="database">
        <n-input v-model:value="formData.database" placeholder="数据库名" />
      </n-form-item>
      <n-form-item label="用户名" path="username">
        <n-input v-model:value="formData.username" placeholder="连接用户名" />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input v-model:value="formData.password" type="password" show-password-on="click" :placeholder="isEdit ? '留空则不修改' : '连接密码'" />
      </n-form-item>
      <n-form-item label="描述">
        <n-input v-model:value="formData.description" type="textarea" placeholder="可选描述" />
      </n-form-item>
      <n-form-item label="表黑名单">
        <n-dynamic-tags v-model:value="tableBlacklist" />
        <template #feedback>
          <n-text depth="3" style="font-size: 12px">支持通配符，如 sys_*、tmp_*，匹配的表不对外暴露</n-text>
        </template>
      </n-form-item>
      <n-form-item label="字段黑名单">
        <n-dynamic-tags v-model:value="columnBlacklist" />
        <template #feedback>
          <n-text depth="3" style="font-size: 12px">匹配的字段名不对外暴露，如 password、secret_*</n-text>
        </template>
      </n-form-item>
      <n-space>
        <n-button type="primary" :loading="submitting" @click="handleSubmit">保存</n-button>
        <n-button @click="router.back()">取消</n-button>
      </n-space>
    </n-form>
  </n-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { getDatasource, createDatasource, updateDatasource } from '@/api/datasource'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const isEdit = computed(() => !!route.params.id)
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const formData = ref({
  name: '',
  type: '' as string | null,
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
  description: '',
})

const tableBlacklist = ref<string[]>([])
const columnBlacklist = ref<string[]>([])

const typeOptions = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'SQL Server', value: 'mssql' },
  { label: 'Oracle', value: 'oracle' },
]

const rules: FormRules = {
  name: { required: true, message: '请输入名称', trigger: 'blur' },
  type: { required: true, message: '请选择类型', trigger: 'change' },
  host: { required: true, message: '请输入主机', trigger: 'blur' },
  port: { required: true, type: 'number', message: '请输入端口', trigger: 'blur' },
  database: { required: true, message: '请输入数据库名', trigger: 'blur' },
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const payload: any = {
      ...formData.value,
      table_blacklist: JSON.stringify(tableBlacklist.value),
      column_blacklist: JSON.stringify(columnBlacklist.value),
    }
    if (isEdit.value) {
      if (!payload.password) delete payload.password
      await updateDatasource(Number(route.params.id), payload)
      message.success('更新成功')
    } else {
      await createDatasource(payload)
      message.success('创建成功')
    }
    router.push('/datasource')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (isEdit.value) {
    const data = await getDatasource(Number(route.params.id))
    formData.value = { ...data, password: '', description: data.description || '' } as any
    try { tableBlacklist.value = JSON.parse((data as any).table_blacklist || '[]') } catch { tableBlacklist.value = [] }
    try { columnBlacklist.value = JSON.parse((data as any).column_blacklist || '[]') } catch { columnBlacklist.value = [] }
  }
})
</script>
