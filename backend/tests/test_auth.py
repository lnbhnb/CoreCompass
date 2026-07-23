import pytest
from app.services import auth_service


def test_register_returns_user_and_token():
    result = auth_service.register("alice", "pw123", "爱丽丝")
    assert result["user"]["username"] == "alice"
    assert result["user"]["display_name"] == "爱丽丝"
    assert len(result["token"]) == 64


def test_register_duplicate_username_raises():
    auth_service.register("bob", "pw", "鲍勃")
    with pytest.raises(ValueError, match="用户名已存在"):
        auth_service.register("bob", "pw", "鲍勃2")


def test_login_correct_password_returns_token():
    auth_service.register("carol", "secret", "卡罗尔")
    result = auth_service.login("carol", "secret")
    assert result["user"]["username"] == "carol"
    assert len(result["token"]) == 64


def test_login_wrong_password_raises():
    auth_service.register("dave", "right", "戴夫")
    with pytest.raises(ValueError, match="用户名或密码错误"):
        auth_service.login("dave", "wrong")


def test_login_unknown_user_raises():
    with pytest.raises(ValueError, match="用户名或密码错误"):
        auth_service.login("nobody", "x")


def test_logout_clears_token():
    result = auth_service.register("eve", "pw", "伊芙")
    auth_service.logout(result["token"])
    from app import models
    assert models.get_user_by_token(result["token"]) is None


def test_password_not_stored_plaintext():
    auth_service.register("frank", "plaintext", "弗兰克")
    from app import models
    user = models.get_user_by_username("frank")
    assert "plaintext" not in user["password_hash"]


def test_login_returns_new_token_each_time():
    auth_service.register("grace", "pw", "格蕾丝")
    t1 = auth_service.login("grace", "pw")["token"]
    t2 = auth_service.login("grace", "pw")["token"]
    assert t1 != t2  # 每次登录签发新 token
