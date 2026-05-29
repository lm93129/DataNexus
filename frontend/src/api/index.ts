import axios from 'axios'
import { getToken, removeToken } from '@/utils/token'
import router from '@/router'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const apiBaseUrl = configuredApiBaseUrl || '/api/v1'

const request = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const ERROR_MESSAGES: Record<number, string> = {
  401: '登录已过期，请重新登录',
  403: '权限不足，无法执行此操作',
  404: '请求的资源不存在',
  422: '请求参数有误，请检查输入',
  429: '请求过于频繁，请稍后再试',
  500: '服务器内部错误，请稍后重试',
  502: '网关错误，请稍后重试',
  503: '服务暂时不可用，请稍后重试',
}

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      removeToken()
      router.push('/login')
    }
    // 统一注入可读错误信息
    const serverMsg = error.response?.data?.detail
    const fallbackMsg = ERROR_MESSAGES[status] || '网络请求失败，请检查网络连接'
    error.displayMessage = serverMsg || fallbackMsg
    return Promise.reject(error)
  }
)

export default request
