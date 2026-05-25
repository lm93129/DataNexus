<template>
  <n-tabs type="line">
    <n-tab-pane name="users" tab="用户管理">
      <n-space vertical :size="16">
        <n-space justify="end">
          <n-button type="primary" @click="showCreateModal = true">新增用户</n-button>
        </n-space>
        <n-data-table :columns="userColumns" :data="users" :loading="loading" />
        <n-empty v-if="loadError" :description="loadError" />
      </n-space>
    </n-tab-pane>
    <n-tab-pane name="password" tab="修改密码">
      <n-card style="max-width: 400px">
        <n-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules">
          <n-form-item label="当前密码" path="old_password">
            <n-input v-model:value="pwdForm.old_password" type="password" />
          </n-form-item>
          <n-form-item label="新密码" path="new_password">
            <n-input v-model:value="pwdForm.new_password" type="password" />
          </n-form-item>
          <n-form-item label="确认密码" path="confirm_password">
            <n-input v-model:value="pwdForm.confirm_password" type="password" />
          </n-form-item>
          <n-button type="primary" @click="handleChangePassword">修改密码</n-button>
        </n-form>
      </n-card>
    </n-tab-pane>
  </n-tabs>

  <n-modal v-model:show="showCreateModal" title="新增用户" preset="dialog">
    <n-form ref="createFormRef" :model="createForm" :rules="createRules">
      <n-form-item label="用户名" path="username">
        <n-input v-model:value="createForm.username" />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input v-model:value="createForm.password" type="password" />
      </n-form-item>
      <n-form-item label="角色" path="role">
        <n-select v-model:value="createForm.role" :options="roleOptions" />
      </n-form-item>
    </n-form>
    <template #action>
      <n-button @click="showCreateModal = false">取消</n-button>
      <n-button type="primary" :loading="creating" @click="handleCreateUser">创建</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NSpace, useMessage, useDialog, type FormInst, type FormRules } from 'naive-ui'
import { listUsers, createUser, deleteUser, changePassword, type User } from '@/api/user'

const message = useMessage()
const dialog = useDialog()
const users = ref<User[]>([])
const loading = ref(false)
const loadError = ref('')
const showCreateModal = ref(false)
const creating = ref(false)

const createFormRef = ref<FormInst | null>(null)
const createForm = ref({ username: '', password: '', role: 'viewer' })
const createRules: FormRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
  role: { required: true, message: '请选择角色', trigger: 'change' },
}

const pwdFormRef = ref<FormInst | null>(null)
const pwdForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const pwdRules: FormRules = {
  old_password: { required: true, message: '请输入当前密码', trigger: 'blur' },
  new_password: { required: true, message: '请输入新密码', trigger: 'blur' },
  confirm_password: {
    required: true,
    trigger: 'blur',
    validator: (_rule: any, value: string) => {
      if (value !== pwdForm.value.new_password) return new Error('两次密码不一致')
      return true
    },
  },
}

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '编辑者', value: 'editor' },
  { label: '查看者', value: 'viewer' },
]

const userColumns = [
  { title: '用户名', key: 'username' },
  {
    title: '角色',
    key: 'role',
    render: (row: User) => h(NTag, { type: row.role === 'admin' ? 'error' : row.role === 'editor' ? 'warning' : 'default', size: 'small' }, () => row.role),
  },
  {
    title: '状态',
    key: 'is_active',
    render: (row: User) => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, () => row.is_active ? '启用' : '禁用'),
  },
  { title: '创建时间', key: 'created_at' },
  {
    title: '操作',
    key: 'actions',
    render: (row: User) =>
      h(NSpace, null, () => [
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteUser(row) }, () => '删除'),
      ]),
  },
]

async function fetchUsers() {
  loading.value = true
  loadError.value = ''
  try {
    users.value = await listUsers()
  } catch {
    loadError.value = '用户管理接口暂未就绪'
  } finally {
    loading.value = false
  }
}

async function handleCreateUser() {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    await createUser(createForm.value)
    message.success('创建成功')
    showCreateModal.value = false
    createForm.value = { username: '', password: '', role: 'viewer' }
    fetchUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function handleDeleteUser(row: User) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除用户「${row.username}」吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteUser(row.id)
      message.success('删除成功')
      fetchUsers()
    },
  })
}

async function handleChangePassword() {
  try {
    await pwdFormRef.value?.validate()
  } catch {
    return
  }
  try {
    await changePassword({ old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
    message.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '修改失败')
  }
}

onMounted(fetchUsers)
</script>
