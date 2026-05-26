import request from './index'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
}

export interface UserProfile {
  id: number
  name: string
  identity_type: string
  role: string
  is_active: boolean
  has_api_key: boolean
}

export function login(data: LoginParams): Promise<LoginResult> {
  return request.post('/auth/login', data)
}

export function getMe(): Promise<UserProfile> {
  return request.get('/auth/me')
}
