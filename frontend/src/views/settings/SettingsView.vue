<template>
  <n-spin :show="!userLoaded" style="min-height: 200px">
    <n-tabs v-if="userLoaded" type="line" :default-value="isAdmin ? 'users' : 'password'">
      <n-tab-pane v-if="isAdmin" name="users" tab="用户管理">
      <n-space vertical :size="16">
        <n-space justify="end">
          <n-button type="primary" @click="openCreate">新增用户</n-button>
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
    <n-tab-pane name="apikey" tab="我的 API Key">
      <n-card style="max-width: 500px">
        <n-space vertical :size="16">
          <n-text>API Key 可用于 MCP 协议接入和 REST API 调用，无需 JWT Token。</n-text>
          <n-spin :show="loadingMyKey">
            <n-alert v-if="myApiKey" type="info" title="当前 API Key">
              <n-text code style="word-break: break-all">{{ myApiKey }}</n-text>
            </n-alert>
            <n-alert v-else type="default" title="未配置">
              <n-text>当前未生成 API Key。</n-text>
            </n-alert>
          </n-spin>
          <n-space>
            <n-button type="primary" @click="handleGenerateMyKey">{{ myApiKey ? '重新生成' : '生成 Key' }}</n-button>
            <n-button v-if="myApiKey" type="error" @click="handleRevokeMyKey">撤销 Key</n-button>
          </n-space>
          <n-text v-if="myApiKey" depth="3" style="font-size: 12px">重新生成后，之前的 Key 将立即失效。</n-text>
        </n-space>
      </n-card>
    </n-tab-pane>
  </n-tabs>
  </n-spin>

  <!-- 新建用户弹窗 -->
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

  <!-- 编辑用户弹窗 -->
  <n-modal v-model:show="showEditModal" title="编辑用户" preset="dialog">
    <n-form :model="editForm">
      <n-form-item label="用户名">
        <n-input :value="editingUser?.username" disabled />
      </n-form-item>
      <n-form-item label="角色">
        <n-select v-model:value="editForm.role" :options="roleOptions" />
      </n-form-item>
      <n-form-item label="状态">
        <n-switch v-model:value="editForm.is_active" />
        <n-text depth="3" style="margin-left: 8px">{{ editForm.is_active ? '启用' : '禁用' }}</n-text>
      </n-form-item>
      <n-form-item label="重置密码">
        <n-input v-model:value="editForm.reset_password" type="password" placeholder="留空则不修改" />
      </n-form-item>
    </n-form>
    <template #action>
      <n-button @click="showEditModal = false">取消</n-button>
      <n-button type="primary" @click="handleUpdateUser">保存</n-button>
    </template>
  </n-modal>

  <!-- Key 生成结果弹窗 -->
  <n-modal v-model:show="showKeyResult" title="API Key 已生成" preset="dialog">
    <n-alert type="success">
      <n-text code style="word-break: break-all">{{ keyResult }}</n-text>
      <n-text depth="3" style="display: block; margin-top: 8px">请立即复制保存，此 Key 仅显示一次。</n-text>
    </n-alert>
    <template #action>
      <n-button type="primary" @click="showKeyResult = false">已复制</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, computed, onMounted } from 'vue'
import { NButton, NTag, NSpace, useMessage, useDialog, type FormInst, type FormRules } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import {
  listUsers, createUser, updateUser, deleteUser, changePassword,
  generateApiKey, getMyApiKey, revokeApiKey, generateApiKeyForUser, revokeApiKeyForUser,
  type User, type UserUpdate,
} from '@/api/user'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')
const userLoaded = ref(false)
const message = useMessage()
const dialog = useDialog()
const users = ref<User[]>([])
const loading = ref(false)
const loadError = ref('')
const showCreateModal = ref(false)
const creating = ref(false)
const myApiKey = ref<string | null>(null)
const loadingMyKey = ref(false)

const showEditModal = ref(false)
const editingUser = ref<User | null>(null)
const editForm = ref<{ role: string; is_active: boolean; reset_password: string }>({ role: 'viewer', is_active: true, reset_password: '' })

const showKeyResult = ref(false)
const keyResult = ref('')

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
  { label: '分析师', value: 'analyst' },
  { label: '查看者', value: 'viewer' },
]

const userColumns = [
  { title: '用户名', key: 'username' },
  {
    title: '角色',
    key: 'role',
    render: (row: User) => h(NTag, { type: row.role === 'admin' ? 'error' : row.role === 'analyst' ? 'warning' : 'default', size: 'small' }, () => row.role),
  },
  {
    title: '状态',
    key: 'is_active',
    render: (row: User) => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, () => row.is_active ? '启用' : '禁用'),
  },
  {
    title: 'API Key',
    key: 'has_api_key',
    render: (row: User) => h(NTag, { type: row.has_api_key ? 'info' : 'default', size: 'small' }, () => row.has_api_key ? '已配置' : '未配置'),
  },
  { title: '创建时间', key: 'created_at' },
  {
    title: '操作',
    key: 'actions',
    width: 320,
    render: (row: User) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'small', onClick: () => openEdit(row) }, () => '编辑'),
        row.has_api_key
          ? h(NButton, { size: 'small', type: 'warning', onClick: () => handleRevokeKey(row) }, () => '撤销Key')
          : h(NButton, { size: 'small', type: 'info', onClick: () => handleGenerateKey(row) }, () => '生成Key'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteUser(row) }, () => '删除'),
      ]),
  },
]

function openCreate() {
  createForm.value = { username: '', password: '', role: 'viewer' }
  showCreateModal.value = true
}

function openEdit(row: User) {
  editingUser.value = row
  editForm.value = { role: row.role, is_active: row.is_active, reset_password: '' }
  showEditModal.value = true
}

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
  try { await createFormRef.value?.validate() } catch { return }
  creating.value = true
  try {
    await createUser(createForm.value)
    message.success('创建成功')
    showCreateModal.value = false
    fetchUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleUpdateUser() {
  if (!editingUser.value) return
  const data: UserUpdate = { role: editForm.value.role, is_active: editForm.value.is_active }
  if (editForm.value.reset_password) data.reset_password = editForm.value.reset_password
  try {
    await updateUser(editingUser.value.id, data)
    message.success('更新成功')
    showEditModal.value = false
    fetchUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '更新失败')
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

async function handleGenerateKey(row: User) {
  try {
    const res = await generateApiKeyForUser(row.id)
    keyResult.value = res.api_key
    showKeyResult.value = true
    fetchUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '生成失败')
  }
}

async function handleRevokeKey(row: User) {
  dialog.warning({
    title: '确认撤销',
    content: `确定撤销用户「${row.username}」的 API Key 吗？撤销后该 Key 立即失效。`,
    positiveText: '撤销',
    negativeText: '取消',
    onPositiveClick: async () => {
      await revokeApiKeyForUser(row.id)
      message.success('已撤销')
      fetchUsers()
    },
  })
}

async function handleChangePassword() {
  try { await pwdFormRef.value?.validate() } catch { return }
  try {
    await changePassword({ old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
    message.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '修改失败')
  }
}

async function fetchMyKey() {
  loadingMyKey.value = true
  try {
    const res = await getMyApiKey()
    myApiKey.value = res.api_key
  } catch {
    myApiKey.value = null
  } finally {
    loadingMyKey.value = false
  }
}

async function handleGenerateMyKey() {
  if (myApiKey.value) {
    dialog.warning({
      title: '确认重新生成',
      content: '重新生成后，当前 Key 将立即失效，确定继续？',
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          const res = await generateApiKey()
          myApiKey.value = res.api_key
          message.success('API Key 已重新生成')
        } catch (e: any) {
          message.error(e.response?.data?.detail || '生成失败')
        }
      },
    })
  } else {
    try {
      const res = await generateApiKey()
      myApiKey.value = res.api_key
      message.success('API Key 已生成')
    } catch (e: any) {
      message.error(e.response?.data?.detail || '生成失败')
    }
  }
}

async function handleRevokeMyKey() {
  dialog.warning({
    title: '确认撤销',
    content: '撤销后 Key 立即失效，确定继续？',
    positiveText: '撤销',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await revokeApiKey()
        myApiKey.value = null
        message.success('API Key 已撤销')
      } catch (e: any) {
        message.error(e.response?.data?.detail || '撤销失败')
      }
    },
  })
}

onMounted(async () => {
  if (!authStore.user) await authStore.fetchUser()
  userLoaded.value = true
  if (isAdmin.value) fetchUsers()
  fetchMyKey()
})
</script>
