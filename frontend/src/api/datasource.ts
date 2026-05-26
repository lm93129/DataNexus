import request from './index'

export interface Datasource {
  id: number
  name: string
  type: string
  host: string
  port: number
  database: string
  username: string
  description?: string
  is_active: boolean
  table_blacklist?: string
  column_blacklist?: string
  created_at: string
}

export interface DatasourceCreate {
  name: string
  type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  description?: string
  table_blacklist?: string
  column_blacklist?: string
}

export function listDatasources(): Promise<Datasource[]> {
  return request.get('/datasources')
}

export function getDatasource(id: number): Promise<Datasource> {
  return request.get(`/datasources/${id}`)
}

export function createDatasource(data: DatasourceCreate): Promise<Datasource> {
  return request.post('/datasources', data)
}

export function updateDatasource(id: number, data: Partial<DatasourceCreate>): Promise<Datasource> {
  return request.put(`/datasources/${id}`, data)
}

export function deleteDatasource(id: number): Promise<void> {
  return request.delete(`/datasources/${id}`)
}

export function testDatasourceConnection(id: number): Promise<{ success: boolean; message: string }> {
  return request.post(`/datasources/${id}/test`)
}
