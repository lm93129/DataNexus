import request from './index'

export interface AlertRule {
  id: number
  name: string
  rule_type: string
  threshold_config: Record<string, number>
  scope: string
  target_id: number | null
  is_active: boolean
  suppress_minutes: number
  created_at: string | null
}

export interface AlertRecord {
  id: number
  rule_id: number
  rule_name: string
  rule_type: string
  detail: string
  status: string
  triggered_at: string | null
  resolved_at: string | null
}

export function listAlertRules(): Promise<AlertRule[]> {
  return request.get('/alerts/rules')
}

export function createAlertRule(data: Partial<AlertRule>): Promise<AlertRule> {
  return request.post('/alerts/rules', data)
}

export function updateAlertRule(id: number, data: Partial<AlertRule>): Promise<AlertRule> {
  return request.put(`/alerts/rules/${id}`, data)
}

export function deleteAlertRule(id: number): Promise<void> {
  return request.delete(`/alerts/rules/${id}`)
}

export function listAlertRecords(status?: string, limit?: number): Promise<AlertRecord[]> {
  return request.get('/alerts/records', { params: { status, limit } })
}

export function getPendingAlertCount(): Promise<{ count: number }> {
  return request.get('/alerts/records/pending-count')
}

export function acknowledgeAlert(id: number): Promise<void> {
  return request.put(`/alerts/records/${id}/acknowledge`)
}

export function resolveAlert(id: number): Promise<void> {
  return request.put(`/alerts/records/${id}/resolve`)
}
