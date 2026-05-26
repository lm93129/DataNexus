import type { Router } from 'vue-router'
import { getToken, isTokenExpired, removeToken } from '@/utils/token'

export function setupGuard(router: Router) {
  router.beforeEach((to, _from, next) => {
    const token = getToken()
    const expired = token ? isTokenExpired() : true

    if (to.meta.requiresAuth !== false && (!token || expired)) {
      // token 不存在或已过期，清除并跳转登录
      if (token && expired) {
        removeToken()
      }
      next('/login')
    } else if (to.path === '/login' && token && !expired) {
      next('/dashboard')
    } else {
      next()
    }
  })
}
