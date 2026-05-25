import request from './index'

export interface User {
  id: number
  username: string
  role: string
  is_active: boolean
  has_api_key: boolean
  created_at: string
}

export interface UserCreate {
  username: string
  password: string
  role: string
}

export interface UserUpdate {
  role?: string
  is_active?: boolean
  reset_password?: string
}

export function listUsers(): Promise<User[]> {
  return request.get('/users')
}

export function createUser(data: UserCreate): Promise<User> {
  return request.post('/users', data)
}

export function updateUser(id: number, data: UserUpdate): Promise<User> {
  return request.put(`/users/${id}`, data)
}

export function deleteUser(id: number): Promise<void> {
  return request.delete(`/users/${id}`)
}

export function changePassword(data: { old_password: string; new_password: string }): Promise<void> {
  return request.post('/users/change-password', data)
}

export function generateApiKeyForUser(userId: number): Promise<{ api_key: string; message: string }> {
  return request.post(`/users/${userId}/api-key`)
}

export function getApiKeyForUser(userId: number): Promise<{ api_key: string | null }> {
  return request.get(`/users/${userId}/api-key`)
}

export function revokeApiKeyForUser(userId: number): Promise<{ message: string }> {
  return request.delete(`/users/${userId}/api-key`)
}

export function generateApiKey(): Promise<{ api_key: string; message: string }> {
  return request.post('/auth/api-key/generate')
}

export function getMyApiKey(): Promise<{ api_key: string | null }> {
  return request.get('/auth/api-key/current')
}

export function revokeApiKey(): Promise<{ message: string }> {
  return request.delete('/auth/api-key')
}
