import axios from 'axios'
import { getToken, removeToken } from '@/utils/token'
import router from '@/router'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      removeToken()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request
