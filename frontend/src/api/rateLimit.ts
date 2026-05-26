import request from './index'

export interface RateLimitRule {
  id: number
  name: string
  scope: string
  target_id: number | null
  max_per_minute: number | null
  max_per_hour: number | null
  max_per_day: number | null
  max_rows_per_query: number | null
  is_active: boolean
}

export interface RateLimitCreate {
  name: string
  scope: string
  target_id?: number | null
  max_per_minute?: number | null
  max_per_hour?: number | null
  max_per_day?: number | null
  max_rows_per_query?: number | null
  is_active?: boolean
}

export function listRateLimits(): Promise<RateLimitRule[]> {
  return request.get('/rate-limits')
}

export function createRateLimit(data: RateLimitCreate): Promise<RateLimitRule> {
  return request.post('/rate-limits', data)
}

export function updateRateLimit(id: number, data: Partial<RateLimitCreate>): Promise<RateLimitRule> {
  return request.put(`/rate-limits/${id}`, data)
}

export function deleteRateLimit(id: number): Promise<void> {
  return request.delete(`/rate-limits/${id}`)
}
