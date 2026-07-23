from app.services import validate_service

VALID_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
"""
EMPTY_SQL = "-- nothing here"
NO_FK_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE logs (id INTEGER PRIMARY KEY, msg TEXT);
"""


def test_valid_sql_passes():
    r = validate_service.validate_sql(VALID_SQL)
    assert r["pass"] is True and not r["reasons"]


def test_empty_sql_fails():
    r = validate_service.validate_sql(EMPTY_SQL)
    assert r["pass"] is False
    assert any("表" in x for x in r["reasons"])


def test_no_fk_fails():
    r = validate_service.validate_sql(NO_FK_SQL)
    assert r["pass"] is False
    assert any("外键" in x for x in r["reasons"])
