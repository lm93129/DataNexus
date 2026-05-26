import request from './index'

export interface DashboardStats {
  datasource_count: number
  query_count_today: number
  active_users: number
  error_rate: number
}

export interface QueryTrend {
  time: string
  count: number
}

export interface TopUser {
  user_id: number
  username: string
  count: number
}

export interface TopDatasource {
  datasource: string
  count: number
}

export interface SlowQuery {
  id: number
  identity_id: number
  resource: string
  sql: string | null
  duration_ms: number
  status: string
  created_at: string
}

export interface ErrorStat {
  date: string
  total: number
  errors: number
  success: number
  error_rate: number
}

export function getStats(): Promise<DashboardStats> {
  return request.get('/dashboard/stats')
}

export function getQueryTrend(days: number = 7): Promise<QueryTrend[]> {
  return request.get('/dashboard/query-trend', { params: { days } })
}

export function getHourlyTrend(hours: number = 24): Promise<QueryTrend[]> {
  return request.get('/dashboard/hourly-trend', { params: { hours } })
}

export function getTopUsers(days: number = 7, limit: number = 10): Promise<TopUser[]> {
  return request.get('/dashboard/top-users', { params: { days, limit } })
}

export function getTopDatasources(days: number = 7, limit: number = 10): Promise<TopDatasource[]> {
  return request.get('/dashboard/top-datasources', { params: { days, limit } })
}

export function getSlowQueries(days: number = 7, threshold_ms: number = 1000): Promise<SlowQuery[]> {
  return request.get('/dashboard/slow-queries', { params: { days, threshold_ms } })
}

export function getErrorStats(days: number = 7): Promise<ErrorStat[]> {
  return request.get('/dashboard/error-stats', { params: { days } })
}
