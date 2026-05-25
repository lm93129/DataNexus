import request from './index'

export interface User {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  username: string
  password: string
  role: string
}

export function listUsers(): Promise<User[]> {
  return request.get('/users')
}

export function createUser(data: UserCreate): Promise<User> {
  return request.post('/users', data)
}

export function updateUser(id: number, data: Partial<UserCreate>): Promise<User> {
  return request.put(`/users/${id}`, data)
}

export function deleteUser(id: number): Promise<void> {
  return request.delete(`/users/${id}`)
}

export function changePassword(data: { old_password: string; new_password: string }): Promise<void> {
  return request.post('/users/change-password', data)
}
