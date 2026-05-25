"""
RBAC 权限矩阵单元测试

测试 _has_permission 函数在各角色下的权限判断是否符合预期。
"""
import pytest
from app.core.permissions import _has_permission


class TestPermissionMatrix:
    def test_admin_has_all_permissions(self):
        """admin 拥有所有资源的所有操作权限"""
        assert _has_permission("admin", "datasource:create") is True
        assert _has_permission("admin", "query:execute") is True
        assert _has_permission("admin", "audit:read") is True
        assert _has_permission("admin", "user:manage") is True

    def test_analyst_can_query(self):
        """analyst 可以执行查询"""
        assert _has_permission("analyst", "query:execute") is True

    def test_analyst_can_read_metadata(self):
        """analyst 可以读取元数据"""
        assert _has_permission("analyst", "metadata:read") is True

    def test_analyst_can_read_datasource(self):
        """analyst 可以读取数据源"""
        assert _has_permission("analyst", "datasource:read") is True

    def test_analyst_cannot_manage_datasource(self):
        """analyst 不能创建或删除数据源"""
        assert _has_permission("analyst", "datasource:create") is False
        assert _has_permission("analyst", "datasource:delete") is False

    def test_analyst_cannot_manage_users(self):
        """analyst 不能管理用户"""
        assert _has_permission("analyst", "user:manage") is False

    def test_viewer_can_only_read_metadata(self):
        """viewer 只能读取元数据，不能执行查询或管理数据源"""
        assert _has_permission("viewer", "metadata:read") is True
        assert _has_permission("viewer", "query:execute") is False
        assert _has_permission("viewer", "datasource:create") is False
        assert _has_permission("viewer", "audit:read") is False

    def test_unknown_role_has_no_permissions(self):
        """未知角色没有任何权限"""
        assert _has_permission("unknown", "metadata:read") is False
