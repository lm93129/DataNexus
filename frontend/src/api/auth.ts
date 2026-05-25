import request from './index'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
}

export function login(data: LoginParams): Promise<LoginResult> {
  return request.post('/auth/login', data)
}

export function getMe(): Promise<Record<string, unknown>> {
  return request.get('/auth/me')
}
