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

export interface NotificationChannel {
  id: number
  name: string
  channel_type: string
  webhook_url: string
  is_active: boolean
  created_at: string | null
}

// ========== 告警规则 ==========

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

// ========== 告警记录 ==========

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

// ========== 通知渠道 ==========

export function listChannels(): Promise<NotificationChannel[]> {
  return request.get('/alerts/channels')
}

export function createChannel(data: Partial<NotificationChannel>): Promise<NotificationChannel> {
  return request.post('/alerts/channels', data)
}

export function updateChannel(id: number, data: Partial<NotificationChannel>): Promise<NotificationChannel> {
  return request.put(`/alerts/channels/${id}`, data)
}

export function deleteChannel(id: number): Promise<void> {
  return request.delete(`/alerts/channels/${id}`)
}

export function testChannel(id: number): Promise<{ success: boolean; message: string }> {
  return request.post(`/alerts/channels/${id}/test`)
}

export function getRuleChannels(ruleId: number): Promise<number[]> {
  return request.get(`/alerts/rules/${ruleId}/channels`)
}

export function setRuleChannels(ruleId: number, channelIds: number[]): Promise<void> {
  return request.put(`/alerts/rules/${ruleId}/channels`, { channel_ids: channelIds })
}
