import type { Router } from 'vue-router'
import { getToken } from '@/utils/token'

export function setupGuard(router: Router) {
  router.beforeEach((to, _from, next) => {
    const token = getToken()
    if (to.meta.requiresAuth !== false && !token) {
      next('/login')
    } else if (to.path === '/login' && token) {
      next('/dashboard')
    } else {
      next()
    }
  })
}
