import request from './index'

export interface DesensitizeRule {
  id: number | null
  name: string
  pattern: string
  mask_strategy: string
  replacement?: string
  is_builtin: boolean
  created_at?: string
}

export interface DesensitizeRuleCreate {
  name: string
  pattern: string
  mask_strategy: string
  replacement?: string
}

export function listRules(): Promise<DesensitizeRule[]> {
  return request.get('/desensitize-rules')
}

export function createRule(data: DesensitizeRuleCreate): Promise<DesensitizeRule> {
  return request.post('/desensitize-rules', data)
}

export function updateRule(id: number, data: Partial<DesensitizeRuleCreate>): Promise<DesensitizeRule> {
  return request.put(`/desensitize-rules/${id}`, data)
}

export function deleteRule(id: number): Promise<void> {
  return request.delete(`/desensitize-rules/${id}`)
}

export function assignColumnRule(columnId: number, ruleName: string | null): Promise<void> {
  return request.put(`/desensitize-rules/columns/${columnId}/rule`, { rule_name: ruleName })
}
