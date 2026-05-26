import request from './index'

export interface PermissionMatrix {
  roles: string[]
  resources: string[]
  matrix: Record<string, string[]>
}

export function getPermissionMatrix(): Promise<PermissionMatrix> {
  return request.get('/permissions/matrix')
}
