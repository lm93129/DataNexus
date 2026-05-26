<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <router-view />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { zhCN, dateZhCN, type GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#2F54EB',
    primaryColorHover: '#597EF7',
    primaryColorPressed: '#1D39C4',
    primaryColorSuppl: '#2F54EB',
    borderRadius: '6px',
    borderRadiusSmall: '4px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
  },
  Card: {
    borderRadius: '8px',
    boxShadow: '0 1px 2px 0 rgba(0,0,0,0.03), 0 1px 6px -1px rgba(0,0,0,0.02), 0 2px 4px 0 rgba(0,0,0,0.02)',
  },
  Button: {
    borderRadiusMedium: '6px',
    borderRadiusLarge: '8px',
    borderRadiusSmall: '4px',
  },
  Menu: {
    itemColorActive: 'rgba(47, 84, 235, 0.06)',
    itemTextColorActive: '#2F54EB',
    itemIconColorActive: '#2F54EB',
    itemColorActiveHover: 'rgba(47, 84, 235, 0.09)',
    borderRadius: '6px',
  },
  DataTable: {
    borderRadius: '8px',
    thColor: '#fafafa',
  },
  Input: {
    borderRadius: '6px',
  },
  Tag: {
    borderRadius: '4px',
  },
}
</script>
