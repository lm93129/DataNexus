from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.desensitize import DesensitizeRule
from app.models.metadata import ColumnMetadata
from app.services.security import DataDesensitizer


class DesensitizeRuleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def list_builtin(self) -> list[dict]:
        """返回内置规则列表"""
        results = []
        for name, (pattern, _) in DataDesensitizer.BUILTIN_RULES.items():
            results.append({
                "id": None,
                "name": name,
                "pattern": pattern.pattern,
                "mask_strategy": "regex_replace",
                "replacement": None,
                "is_builtin": True,
                "created_at": None,
            })
        return results

    async def list_all(self) -> list[dict]:
        """合并内置规则和自定义规则"""
        builtin = self.list_builtin()
        result = await self.db.execute(select(DesensitizeRule).order_by(DesensitizeRule.id))
        custom = result.scalars().all()
        custom_dicts = [
            {
                "id": r.id,
                "name": r.name,
                "pattern": r.pattern,
                "mask_strategy": r.mask_strategy,
                "replacement": r.replacement,
                "is_builtin": r.is_builtin,
                "created_at": r.created_at,
            }
            for r in custom
        ]
        return builtin + custom_dicts

    async def create(self, data: dict) -> DesensitizeRule:
        rule = DesensitizeRule(**data, is_builtin=False)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update(self, rule_id: int, data: dict) -> DesensitizeRule | None:
        result = await self.db.execute(
            select(DesensitizeRule).where(DesensitizeRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return None
        if rule.is_builtin:
            raise ValueError("内置规则不可修改")
        for key, value in data.items():
            if value is not None:
                setattr(rule, key, value)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete(self, rule_id: int) -> bool:
        result = await self.db.execute(
            select(DesensitizeRule).where(DesensitizeRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return False
        if rule.is_builtin:
            raise ValueError("内置规则不可删除")
        await self.db.delete(rule)
        await self.db.commit()
        return True

    async def assign_to_column(self, column_id: int, rule_name: str | None) -> ColumnMetadata | None:
        """为列分配脱敏规则"""
        result = await self.db.execute(
            select(ColumnMetadata).where(ColumnMetadata.id == column_id)
        )
        col = result.scalar_one_or_none()
        if not col:
            return None
        # 验证规则名存在
        if rule_name:
            builtin_names = set(DataDesensitizer.BUILTIN_RULES.keys())
            if rule_name not in builtin_names:
                db_result = await self.db.execute(
                    select(DesensitizeRule).where(DesensitizeRule.name == rule_name)
                )
                if not db_result.scalar_one_or_none():
                    raise ValueError(f"规则 '{rule_name}' 不存在")
        col.desensitize_rule = rule_name
        await self.db.commit()
        await self.db.refresh(col)
        return col
