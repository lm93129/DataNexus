import request from './index'

export interface TableMeta {
  id: number
  table_name: string
  table_comment?: string
}

export interface ColumnMeta {
  column_name: string
  data_type: string
  column_comment?: string
  is_primary_key: boolean
}

export function getTables(datasourceId: number): Promise<TableMeta[]> {
  return request.get(`/metadata/tables/${datasourceId}`)
}

export function getColumns(tableMetadataId: number): Promise<ColumnMeta[]> {
  return request.get(`/metadata/columns/${tableMetadataId}`)
}
