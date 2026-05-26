<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider
      :collapsed="appStore.sidebarCollapsed"
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      show-trigger
      @collapse="appStore.toggleSidebar"
      @expand="appStore.toggleSidebar"
      :native-scrollbar="false"
      class="app-sider"
    >
      <div class="logo">
        <div class="logo-icon">DN</div>
        <span v-if="!appStore.sidebarCollapsed" class="logo-text">DataNexus</span>
      </div>
      <n-menu
        :collapsed="appStore.sidebarCollapsed"
        :options="menuOptions"
        :value="route.name as string"
        :indent="20"
        @update:value="handleMenuClick"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header class="app-header">
        <div class="header-left">
          <span class="page-title">{{ route.meta.title || '概览' }}</span>
        </div>
        <div class="header-right">
          <n-space align="center" :size="16">
            <n-tag v-if="authStore.user" :bordered="false" type="info" size="small">
              {{ authStore.user.role }}
            </n-tag>
            <span class="username">{{ authStore.user?.name || '' }}</span>
            <n-button text type="error" size="small" @click="handleLogout">退出</n-button>
          </n-space>
        </div>
      </n-layout-header>
      <n-layout-content class="app-content">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ServerOutline,
  GridOutline,
  SearchOutline,
  DocumentTextOutline,
  StatsChartOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  CodeSlashOutline,
  NotificationsOutline,
  LockClosedOutline,
  SpeedometerOutline,
} from '@vicons/ionicons5'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  { label: '监控仪表盘', key: 'Dashboard', icon: renderIcon(StatsChartOutline) },
  { label: '数据源管理', key: 'Datasource', icon: renderIcon(ServerOutline) },
  { label: '元数据浏览', key: 'Metadata', icon: renderIcon(GridOutline) },
  { label: 'SQL 查询', key: 'Query', icon: renderIcon(SearchOutline) },
  { label: '脱敏规则', key: 'Desensitize', icon: renderIcon(ShieldCheckmarkOutline) },
  { label: '自定义 API', key: 'CustomApi', icon: renderIcon(CodeSlashOutline) },
  { label: '审计日志', key: 'Audit', icon: renderIcon(DocumentTextOutline) },
  { label: '异常告警', key: 'Alert', icon: renderIcon(NotificationsOutline) },
  { label: '限流策略', key: 'RateLimit', icon: renderIcon(SpeedometerOutline) },
  { label: '权限管理', key: 'Permissions', icon: renderIcon(LockClosedOutline) },
  { label: '系统设置', key: 'Settings', icon: renderIcon(SettingsOutline) },
]

function handleMenuClick(key: string) {
  router.push({ name: key })
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-sider {
  background: #fff;
  border-right: 1px solid var(--border-light);
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-light);
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2F54EB, #597EF7);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.app-header {
  height: 60px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  z-index: 1;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.username {
  font-size: 14px;
  color: var(--text-secondary);
}

.app-content {
  padding: 24px;
  background: var(--bg-page);
  min-height: calc(100vh - 60px);
}
</style>
