<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider
      bordered
      :collapsed="appStore.sidebarCollapsed"
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      show-trigger
      @collapse="appStore.toggleSidebar"
      @expand="appStore.toggleSidebar"
    >
      <div class="logo">
        <h2 v-if="!appStore.sidebarCollapsed">DataNexus</h2>
        <h2 v-else>DN</h2>
      </div>
      <n-menu
        :collapsed="appStore.sidebarCollapsed"
        :options="menuOptions"
        :value="route.name as string"
        @update:value="handleMenuClick"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header bordered style="height: 60px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between">
        <span>{{ route.meta.title || 'DataNexus' }}</span>
        <n-button text @click="handleLogout">退出登录</n-button>
      </n-layout-header>
      <n-layout-content style="padding: 24px">
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
  { label: 'SQL查询', key: 'Query', icon: renderIcon(SearchOutline) },
  { label: '脱敏规则', key: 'Desensitize', icon: renderIcon(ShieldCheckmarkOutline) },
  { label: '自定义API', key: 'CustomApi', icon: renderIcon(CodeSlashOutline) },
  { label: '审计日志', key: 'Audit', icon: renderIcon(DocumentTextOutline) },
  { label: '异常告警', key: 'Alert', icon: renderIcon(NotificationsOutline) },
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
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--n-border-color);
}
</style>
