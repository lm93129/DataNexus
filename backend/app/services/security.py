import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp


@dataclass
class ValidationResult:
    is_safe: bool
    reason: str = ""


class SqlRiskControl:
    """SQL风控：基于 AST 的安全校验"""

    DANGEROUS_FUNCTIONS = {
        "pg_sleep", "sleep", "benchmark", "waitfor",
        "dbms_pipe.receive_message", "load_file",
        "pg_read_file", "pg_ls_dir",
    }

    def __init__(self, max_rows: int = 1000):
        self.max_rows = max_rows

    def validate(self, sql: str, dialect: str | None = None) -> ValidationResult:
        # 解析 SQL
        try:
            statements = sqlglot.parse(sql, dialect=dialect)
        except sqlglot.errors.ParseError as e:
            return ValidationResult(is_safe=False, reason=f"SQL解析失败: {str(e)}")

        if not statements:
            return ValidationResult(is_safe=False, reason="空SQL语句")

        # 只允许单条语句
        valid_statements = [s for s in statements if s is not None]
        if len(valid_statements) != 1:
            return ValidationResult(is_safe=False, reason="禁止多语句执行")

        stmt = valid_statements[0]

        # 必须是 SELECT（UNION 查询顶层节点是 exp.Union，其子节点均为 SELECT，也允许）
        if not isinstance(stmt, (exp.Select, exp.Union)):
            return ValidationResult(is_safe=False, reason="仅允许SELECT查询语句")

        # 检查危险函数
        for func_node in stmt.find_all(exp.Anonymous, exp.Func):
            func_name = ""
            if isinstance(func_node, exp.Anonymous):
                func_name = func_node.name.lower()
            elif hasattr(func_node, "sql_name"):
                func_name = func_node.sql_name().lower()
            if func_name in self.DANGEROUS_FUNCTIONS:
                return ValidationResult(is_safe=False, reason=f"包含危险函数: {func_name}")

        # 检查 INTO OUTFILE / DUMPFILE
        sql_upper = sql.upper()
        if "INTO OUTFILE" in sql_upper or "INTO DUMPFILE" in sql_upper:
            return ValidationResult(is_safe=False, reason="禁止 INTO OUTFILE/DUMPFILE")

        # 检查 UNION 数量
        unions = list(stmt.find_all(exp.Union))
        if len(unions) > 2:
            return ValidationResult(is_safe=False, reason="UNION拼接超过2个，禁止执行")

        # 检查子查询嵌套深度
        depth = self._subquery_depth(stmt)
        if depth > 3:
            return ValidationResult(is_safe=False, reason="子查询嵌套超过3层")

        # 检查无 WHERE 条件的 SELECT *（全表扫描防护）
        if self._is_unfiltered_select_star(stmt):
            return ValidationResult(is_safe=False, reason="禁止无条件全表扫描：SELECT * 必须包含 WHERE 条件")

        return ValidationResult(is_safe=True)

    def apply_row_limit(self, sql: str, max_rows: int | None = None, dialect: str | None = None) -> str:
        """基于 AST 注入或修改 LIMIT"""
        limit = max_rows or self.max_rows
        try:
            statements = sqlglot.parse(sql, dialect=dialect)
            if not statements or statements[0] is None:
                return sql

            stmt = statements[0]
            existing_limit = stmt.find(exp.Limit)

            if existing_limit:
                limit_expr = existing_limit.expression
                if isinstance(limit_expr, exp.Literal) and limit_expr.is_int:
                    current_limit = int(limit_expr.this)
                    if current_limit > limit:
                        existing_limit.set("expression", exp.Literal.number(limit))
            else:
                stmt = stmt.limit(limit)

            return stmt.sql(dialect=dialect)
        except Exception:
            if "LIMIT" not in sql.upper():
                return f"{sql.rstrip(';')} LIMIT {limit}"
            return sql

    def _subquery_depth(self, node, current: int = 0) -> int:
        max_depth = current
        for child in node.iter_expressions():
            if isinstance(child, exp.Subquery):
                max_depth = max(max_depth, self._subquery_depth(child, current + 1))
            else:
                max_depth = max(max_depth, self._subquery_depth(child, current))
        return max_depth

    def _is_unfiltered_select_star(self, stmt) -> bool:
        """检测无 WHERE 条件的 SELECT *（仅针对直接查询真实表的情况）"""
        # UNION 查询检查每个子 SELECT
        if isinstance(stmt, exp.Union):
            for select_node in stmt.find_all(exp.Select):
                if self._is_unfiltered_select_star(select_node):
                    return True
            return False

        if not isinstance(stmt, exp.Select):
            return False

        # 检查是否为 SELECT *（存在 Star 节点）
        has_star = any(isinstance(expr, exp.Star) for expr in stmt.expressions)
        if not has_star:
            return False

        # 检查 FROM 子句是否直接引用真实表（非子查询/派生表）
        from_clause = stmt.find(exp.From)
        if not from_clause:
            return False

        # 如果 FROM 后面全是子查询/派生表，则不算全表扫描
        has_real_table = False
        for table_node in from_clause.find_all(exp.Table):
            # 排除子查询内部的表引用
            parent_subquery = table_node.find_ancestor(exp.Subquery)
            if parent_subquery and from_clause.find_ancestor(exp.Select) == stmt:
                continue
            has_real_table = True
            break

        if not has_real_table:
            return False

        # 检查是否缺少 WHERE 条件
        where = stmt.find(exp.Where)
        if where:
            return False

        return True


class DataDesensitizer:
    """数据脱敏处理器"""

    BUILTIN_RULES = {
        "phone": (re.compile(r"1[3-9]\d{9}"), lambda m: m.group()[:3] + "****" + m.group()[7:]),
        "id_card": (re.compile(r"\d{17}[\dXx]"), lambda m: m.group()[:3] + "***********" + m.group()[14:]),
        "bank_card": (re.compile(r"\d{16,19}"), lambda m: "****" + m.group()[-4:]),
        "email": (re.compile(r"[\w.]+@[\w.]+"), lambda m: m.group()[0] + "***@" + m.group().split("@")[1]),
    }

    def __init__(self, rules: list[dict] | None = None):
        self.custom_rules = rules or []

    def desensitize_value(self, value: str, rule_name: str | None = None) -> str:
        if not isinstance(value, str):
            return value
        if rule_name and rule_name in self.BUILTIN_RULES:
            pattern, replacer = self.BUILTIN_RULES[rule_name]
            return pattern.sub(replacer, value)
        # 自动检测并脱敏
        for name, (pattern, replacer) in self.BUILTIN_RULES.items():
            value = pattern.sub(replacer, value)
        return value

    def desensitize_row(self, row: dict, column_rules: dict[str, str], auto_detect: bool = True) -> dict:
        """对一行数据按列规则脱敏，无规则的列可选自动检测"""
        result = {}
        for col, val in row.items():
            if col in column_rules and val is not None:
                result[col] = self.desensitize_value(str(val), column_rules[col])
            elif auto_detect and val is not None and isinstance(val, str):
                result[col] = self._auto_detect_and_mask(val)
            else:
                result[col] = val
        return result

    def _auto_detect_and_mask(self, value: str) -> str:
        """自动检测并脱敏敏感数据，使用 fullmatch 避免对普通文本中的数字子串误判"""
        for name, (pattern, replacer) in self.BUILTIN_RULES.items():
            if pattern.fullmatch(value):
                return pattern.sub(replacer, value)
        return value
