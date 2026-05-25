import { createRouter, createWebHistory } from 'vue-router'
import { setupGuard } from './guard'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/dashboard/DashboardView.vue'),
        },
        {
          path: 'datasource',
          name: 'Datasource',
          component: () => import('@/views/datasource/DatasourceList.vue'),
        },
        {
          path: 'datasource/create',
          name: 'DatasourceCreate',
          component: () => import('@/views/datasource/DatasourceForm.vue'),
        },
        {
          path: 'datasource/:id/edit',
          name: 'DatasourceEdit',
          component: () => import('@/views/datasource/DatasourceForm.vue'),
        },
        {
          path: 'metadata',
          name: 'Metadata',
          component: () => import('@/views/metadata/MetadataView.vue'),
        },
        {
          path: 'query',
          name: 'Query',
          component: () => import('@/views/query/QueryView.vue'),
        },
        {
          path: 'audit',
          name: 'Audit',
          component: () => import('@/views/audit/AuditView.vue'),
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/settings/SettingsView.vue'),
        },
      ],
    },
  ],
})

setupGuard(router)

export default router
