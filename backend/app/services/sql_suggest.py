import difflib
import re

import sqlglot

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metadata import ColumnMetadata, TableMetadata


class SqlSuggestionService:
    """SQL 智能纠错：表名/字段名模糊匹配"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_suggestions(self, sql: str, datasource_id: int, error_msg: str = "") -> list[dict]:
        """根据 SQL 和错误信息生成纠错建议"""
        suggestions = []

        # 语法错误检测
        syntax_suggestions = self._check_syntax(sql)
        if syntax_suggestions:
            suggestions.extend(syntax_suggestions)

        # 表名/字段名纠错
        name_suggestions = await self._check_names(sql, datasource_id, error_msg)
        suggestions.extend(name_suggestions)

        return suggestions

    def _check_syntax(self, sql: str) -> list[dict]:
        """检查语法错误并给出建议"""
        try:
            sqlglot.parse(sql)
            return []
        except sqlglot.errors.ParseError as e:
            msg = str(e)
            # 提取错误位置信息
            col_match = re.search(r"col:\s*(\d+)", msg)
            col = int(col_match.group(1)) if col_match else None
            return [{
                "type": "syntax",
                "message": f"语法错误: {msg.split('.')[0]}",
                "position": col,
            }]

    async def _check_names(self, sql: str, datasource_id: int, error_msg: str) -> list[dict]:
        """检查表名和字段名是否存在，不存在时给出相似建议"""
        suggestions = []

        # 获取该数据源所有表名
        table_result = await self.db.execute(
            select(TableMetadata.table_name).where(
                TableMetadata.datasource_id == datasource_id,
                TableMetadata.is_blocked == False,
            )
        )
        all_tables = [row[0] for row in table_result.fetchall()]

        # 从错误信息中提取不存在的表名/字段名
        # PostgreSQL: relation "xxx" does not exist
        rel_match = re.search(r'relation "(\w+)" does not exist', error_msg)
        if rel_match:
            bad_name = rel_match.group(1)
            similar = difflib.get_close_matches(bad_name, all_tables, n=3, cutoff=0.5)
            if similar:
                suggestions.append({
                    "type": "table",
                    "message": f"表 \"{bad_name}\" 不存在",
                    "candidates": similar,
                    "original": bad_name,
                })

        # PostgreSQL: column "xxx" does not exist
        col_match = re.search(r'column "(\w+)" does not exist', error_msg)
        if col_match:
            bad_col = col_match.group(1)
            # 尝试从 SQL 中提取表名来缩小搜索范围
            table_cols = await self._get_all_columns(datasource_id)
            similar = difflib.get_close_matches(bad_col, table_cols, n=3, cutoff=0.5)
            if similar:
                suggestions.append({
                    "type": "column",
                    "message": f"字段 \"{bad_col}\" 不存在",
                    "candidates": similar,
                    "original": bad_col,
                })

        # MySQL: Table 'xxx' doesn't exist / Unknown column 'xxx'
        mysql_table = re.search(r"Table '[\w.]*\.?(\w+)' doesn't exist", error_msg)
        if mysql_table:
            bad_name = mysql_table.group(1)
            similar = difflib.get_close_matches(bad_name, all_tables, n=3, cutoff=0.5)
            if similar:
                suggestions.append({
                    "type": "table",
                    "message": f"表 \"{bad_name}\" 不存在",
                    "candidates": similar,
                    "original": bad_name,
                })

        mysql_col = re.search(r"Unknown column '(\w+)'", error_msg)
        if mysql_col:
            bad_col = mysql_col.group(1)
            table_cols = await self._get_all_columns(datasource_id)
            similar = difflib.get_close_matches(bad_col, table_cols, n=3, cutoff=0.5)
            if similar:
                suggestions.append({
                    "type": "column",
                    "message": f"字段 \"{bad_col}\" 不存在",
                    "candidates": similar,
                    "original": bad_col,
                })

        # 主动检查 SQL 中引用的表名是否存在（不依赖错误信息）
        if not error_msg:
            try:
                stmts = sqlglot.parse(sql)
                if stmts and stmts[0]:
                    for table_node in stmts[0].find_all(sqlglot.exp.Table):
                        tname = table_node.name
                        if tname and tname.lower() not in [t.lower() for t in all_tables]:
                            similar = difflib.get_close_matches(tname, all_tables, n=3, cutoff=0.5)
                            if similar:
                                suggestions.append({
                                    "type": "table",
                                    "message": f"表 \"{tname}\" 不存在",
                                    "candidates": similar,
                                    "original": tname,
                                })
            except Exception:
                pass

        return suggestions

    async def _get_all_columns(self, datasource_id: int) -> list[str]:
        """获取数据源下所有字段名"""
        result = await self.db.execute(
            select(ColumnMetadata.column_name)
            .join(TableMetadata, ColumnMetadata.table_metadata_id == TableMetadata.id)
            .where(
                TableMetadata.datasource_id == datasource_id,
                ColumnMetadata.is_blocked == False,
            )
        )
        return list(set(row[0] for row in result.fetchall()))
