import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getMe, type LoginParams, type UserProfile } from '@/api/auth'
import { getToken, setToken, removeToken } from '@/utils/token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<UserProfile | null>(null)

  const isLoggedIn = () => !!token.value

  async function login(params: LoginParams) {
    const result = await loginApi(params)
    token.value = result.access_token
    setToken(result.access_token)
    return result
  }

  async function fetchUser() {
    if (!token.value) return
    user.value = await getMe()
  }

  function logout() {
    token.value = null
    user.value = null
    removeToken()
  }

  return { token, user, isLoggedIn, login, fetchUser, logout }
})
