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

export function executeQuery(data: QueryParams): Promise<QueryResult> {
  return request.post('/query/execute', data)
}
