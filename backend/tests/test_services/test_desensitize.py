import pytest
from app.services.security import DataDesensitizer


class TestAutoDetect:
    def setup_method(self):
        self.ds = DataDesensitizer()

    def test_auto_detect_phone(self):
        row = {"name": "张三", "contact": "13812345678"}
        result = self.ds.desensitize_row(row, {}, auto_detect=True)
        assert result["contact"] == "138****5678"
        assert result["name"] == "张三"

    def test_auto_detect_id_card(self):
        row = {"id_number": "110101199001011234"}
        result = self.ds.desensitize_row(row, {}, auto_detect=True)
        assert "***" in result["id_number"]
        assert result["id_number"] != "110101199001011234"

    def test_auto_detect_does_not_mask_normal_numbers(self):
        row = {"age": "25", "score": "99.5"}
        result = self.ds.desensitize_row(row, {}, auto_detect=True)
        assert result["age"] == "25"
        assert result["score"] == "99.5"

    def test_explicit_rule_overrides_auto_detect(self):
        row = {"phone": "13812345678"}
        result = self.ds.desensitize_row(row, {"phone": "phone"}, auto_detect=True)
        assert result["phone"] == "138****5678"

    def test_no_auto_detect_when_disabled(self):
        row = {"contact": "13812345678"}
        result = self.ds.desensitize_row(row, {}, auto_detect=False)
        assert result["contact"] == "13812345678"

    def test_non_string_values_not_affected(self):
        row = {"count": 100, "active": True, "data": None}
        result = self.ds.desensitize_row(row, {}, auto_detect=True)
        assert result["count"] == 100
        assert result["active"] is True
        assert result["data"] is None
