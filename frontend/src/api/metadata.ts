import request from './index'

export interface TableMeta {
  id: number
  table_name: string
  table_comment?: string
}

export interface ColumnMeta {
  id: number
  column_name: string
  data_type: string
  column_comment?: string
  is_primary_key: boolean
  desensitize_rule?: string
}

export function getTables(datasourceId: number): Promise<TableMeta[]> {
  return request.get(`/metadata/tables/${datasourceId}`)
}

export function getColumns(tableMetadataId: number): Promise<ColumnMeta[]> {
  return request.get(`/metadata/columns/${tableMetadataId}`)
}

export function syncMetadata(datasourceId: number): Promise<{ success: boolean; table_count: number }> {
  return request.post(`/metadata/sync/${datasourceId}`)
}

export interface SearchResult {
  tables: { id: number; datasource_id: number; table_name: string; table_comment?: string }[]
  columns: { id: number; table_metadata_id: number; column_name: string; data_type: string; column_comment?: string }[]
}

export function searchMetadata(keyword: string, datasourceId?: number): Promise<SearchResult> {
  const params: Record<string, string | number> = { keyword }
  if (datasourceId) params.datasource_id = datasourceId
  return request.get('/metadata/search', { params })
}

export function updateTableComment(tableId: number, comment: string): Promise<{ id: number; table_name: string; table_comment: string }> {
  return request.put(`/metadata/tables/${tableId}/comment`, { comment })
}

export function updateColumnComment(columnId: number, comment: string): Promise<{ id: number; column_name: string; column_comment: string }> {
  return request.put(`/metadata/columns/${columnId}/comment`, { comment })
}
