import request from './index'

export interface AuditLog {
  id: number
  identity_id: number | null
  identity_type: string
  username: string
  action: string
  resource: string
  request_summary?: string
  response_summary?: string
  ip?: string
  duration_ms?: number
  status: string
  created_at: string
}

export interface AuditQuery {
  page?: number
  page_size?: number
  identity_id?: number
  identity_type?: string
  action?: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getAuditLogs(params: AuditQuery): Promise<PaginatedResult<AuditLog>> {
  return request.get('/audit/logs', { params })
}
