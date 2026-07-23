import pytest
from app.services import validate_service


def test_sql_too_large_would_be_rejected_by_route():
    # 路由层有 10MB 限制，此处验证校验函数本身可处理大文本不崩
    big_sql = "CREATE TABLE a (id INTEGER PRIMARY KEY);\n" + "x" * 100000
    r = validate_service.validate_sql(big_sql)
    assert isinstance(r, dict) and "pass" in r


def test_md_validation_minimum():
    short_md = "# Title\n短"
    r = validate_service.validate_md(short_md)
    assert r["pass"] is False
    assert len(r["reasons"]) >= 2  # 字数 + H2 不足


def test_code_empty_file():
    r = validate_service.validate_code("", "py")
    assert r["pass"] is False


def test_json_invalid():
    r = validate_service.validate_json_schema("{not valid json")
    assert r["pass"] is False
    assert any("解析" in x for x in r["reasons"])
