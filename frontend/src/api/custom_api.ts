import request from './index'

export interface CustomApi {
  id: number
  name: string
  description?: string
  mode: string
  config_json: string
  is_active: boolean
  version: number
  created_at?: string
}

export interface CustomApiCreate {
  name: string
  description?: string
  mode: string
  config_json: string
  is_active?: boolean
}

export function listCustomApis(): Promise<CustomApi[]> {
  return request.get('/custom-apis')
}

export function getCustomApi(id: number): Promise<CustomApi> {
  return request.get(`/custom-apis/${id}`)
}

export function createCustomApi(data: CustomApiCreate): Promise<CustomApi> {
  return request.post('/custom-apis', data)
}

export function updateCustomApi(id: number, data: Partial<CustomApiCreate>): Promise<CustomApi> {
  return request.put(`/custom-apis/${id}`, data)
}

export function deleteCustomApi(id: number): Promise<void> {
  return request.delete(`/custom-apis/${id}`)
}

export function testCustomApi(id: number, params?: Record<string, any>): Promise<{ success: boolean; message: string; status_code?: number; body_preview?: string; data?: any }> {
  return request.post(`/custom-apis/${id}/test`, { params: params || {} })
}
