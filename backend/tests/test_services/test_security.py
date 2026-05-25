import pytest
from app.services.security import SqlRiskControl, DataDesensitizer


class TestSqlRiskControl:
    def setup_method(self):
        self.rc = SqlRiskControl(max_rows=1000)

    def test_allow_simple_select(self):
        result = self.rc.validate("SELECT id, name FROM users WHERE id = 1")
        assert result.is_safe is True

    def test_block_delete(self):
        result = self.rc.validate("DELETE FROM users WHERE id = 1")
        assert result.is_safe is False
        assert "仅允许SELECT" in result.reason

    def test_block_drop(self):
        result = self.rc.validate("DROP TABLE users")
        assert result.is_safe is False

    def test_block_update(self):
        result = self.rc.validate("UPDATE users SET name='hack' WHERE 1=1")
        assert result.is_safe is False

    def test_block_insert(self):
        result = self.rc.validate("INSERT INTO users (name) VALUES ('test')")
        assert result.is_safe is False

    def test_block_pg_sleep(self):
        result = self.rc.validate("SELECT pg_sleep(10)")
        assert result.is_safe is False
        assert "危险函数" in result.reason

    def test_block_sleep(self):
        result = self.rc.validate("SELECT sleep(10)")
        assert result.is_safe is False

    def test_block_benchmark(self):
        result = self.rc.validate("SELECT benchmark(1000000, SHA1('test'))")
        assert result.is_safe is False

    def test_block_union_abuse(self):
        sql = "SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4"
        result = self.rc.validate(sql)
        assert result.is_safe is False
        assert "UNION" in result.reason

    def test_block_semicolon_injection(self):
        result = self.rc.validate("SELECT 1; DROP TABLE users")
        assert result.is_safe is False

    def test_block_into_outfile(self):
        result = self.rc.validate("SELECT * FROM users INTO OUTFILE '/tmp/data.csv'")
        assert result.is_safe is False

    def test_allow_subquery_within_limit(self):
        sql = "SELECT * FROM (SELECT id FROM users) AS sub"
        result = self.rc.validate(sql)
        assert result.is_safe is True

    def test_block_deep_subquery(self):
        sql = "SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT id FROM t) a) b) c) d"
        result = self.rc.validate(sql)
        assert result.is_safe is False

    def test_apply_row_limit_adds_limit(self):
        result = self.rc.apply_row_limit("SELECT * FROM orders", max_rows=100)
        assert "100" in result

    def test_apply_row_limit_caps_excessive_limit(self):
        result = self.rc.apply_row_limit("SELECT * FROM orders LIMIT 999999", max_rows=1000)
        assert "999999" not in result
        assert "1000" in result

    def test_apply_row_limit_preserves_small_limit(self):
        result = self.rc.apply_row_limit("SELECT * FROM orders LIMIT 50", max_rows=1000)
        assert "50" in result


class TestDataDesensitizer:
    def setup_method(self):
        self.ds = DataDesensitizer()

    def test_phone_desensitize(self):
        result = self.ds.desensitize_value("13812345678", "phone")
        assert result == "138****5678"

    def test_id_card_desensitize(self):
        result = self.ds.desensitize_value("110101199001011234", "id_card")
        assert result == "110***********1234"

    def test_email_desensitize(self):
        result = self.ds.desensitize_value("test@example.com", "email")
        assert result == "t***@example.com"

    def test_desensitize_row(self):
        row = {"name": "张三", "phone": "13812345678", "age": 25}
        rules = {"phone": "phone"}
        result = self.ds.desensitize_row(row, rules)
        assert result["phone"] == "138****5678"
        assert result["name"] == "张三"
        assert result["age"] == 25
