import request from './index'

export interface QueryParams {
  datasource_id: number
  sql: string
}

export interface QueryResult {
  success: boolean
  columns: string[]
  data: Record<string, unknown>[]
  row_count: number
  duration_ms: number
  error?: string
}

export interface QueryHistoryItem {
  id: number
  datasource_id: number
  sql: string
  status: string
  duration_ms: number | null
  row_count: number | null
  created_at: string | null
}

export function executeQuery(data: QueryParams): Promise<QueryResult> {
  return request.post('/query/execute', data)
}

export function getQueryHistory(): Promise<QueryHistoryItem[]> {
  return request.get('/query/history')
}

export function deleteQueryHistory(id: number): Promise<void> {
  return request.delete(`/query/history/${id}`)
}

export function exportQueryCsv(data: QueryParams): Promise<Blob> {
  return request.post('/query/export', data, { responseType: 'blob' })
}
