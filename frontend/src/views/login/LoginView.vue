<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">DN</div>
        <h1 class="login-title">DataNexus</h1>
        <p class="login-subtitle">企业AI统一数据网关平台</p>
      </div>
      <n-form ref="formRef" :model="formData" :rules="rules">
        <n-form-item label="用户名" path="username">
          <n-input
            v-model:value="formData.username"
            placeholder="请输入用户名"
            size="large"
          />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="formData.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
            size="large"
            @keyup.enter="handleLogin"
          />
        </n-form-item>
        <n-button
          type="primary"
          block
          size="large"
          :loading="loading"
          @click="handleLogin"
          style="margin-top: 8px"
        >
          登录
        </n-button>
      </n-form>
      <div class="login-footer">
        <span>安全访问 · 全面审计 · 数据脱敏</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const formData = ref({ username: '', password: '' })

const rules: FormRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

async function handleLogin() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await authStore.login(formData.value)
    message.success('登录成功')
    router.push('/dashboard')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1D39C4 0%, #2F54EB 50%, #597EF7 100%);
  position: relative;
  overflow: hidden;
}

.login-container::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(ellipse at 30% 20%, rgba(255,255,255,0.08) 0%, transparent 50%);
  pointer-events: none;
}

.login-card {
  width: 400px;
  padding: 40px 36px 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2F54EB, #597EF7);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-light);
}

.login-footer span {
  font-size: 12px;
  color: var(--text-placeholder);
  letter-spacing: 0.5px;
}
</style>
