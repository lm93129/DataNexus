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

export function getStats(): Promise<DashboardStats> {
  return request.get('/dashboard/stats')
}

export function getQueryTrend(days: number = 7): Promise<QueryTrend[]> {
  return request.get('/dashboard/query-trend', { params: { days } })
}
