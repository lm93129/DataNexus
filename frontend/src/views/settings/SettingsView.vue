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
    <n-tab-pane v-if="isAdmin" name="ratelimit" tab="限流策略">
      <n-space vertical :size="16">
        <n-space justify="end">
          <n-button type="primary" @click="openCreateRule">新增规则</n-button>
        </n-space>
        <n-data-table :columns="rlColumns" :data="rlRules" :loading="rlLoading" />
      </n-space>
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
import { ref, h, computed, onMounted } from 'vue'
import { NButton, NTag, NSpace, NSwitch, useMessage, useDialog, type FormInst, type FormRules } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import {
  listUsers, createUser, updateUser, deleteUser, changePassword,
  generateApiKey, getMyApiKey, revokeApiKey, generateApiKeyForUser, revokeApiKeyForUser,
  type User, type UserUpdate,
} from '@/api/user'
import { listRateLimits, createRateLimit, updateRateLimit, deleteRateLimit, type RateLimitRule } from '@/api/rateLimit'

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

// ========== 限流策略管理 ==========
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

onMounted(async () => {
  if (!authStore.user) await authStore.fetchUser()
  userLoaded.value = true
  if (isAdmin.value) {
    fetchUsers()
    fetchRlRules()
  }
  fetchMyKey()
})
</script>
