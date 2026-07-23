import pytest
from fastapi import HTTPException
from app.services import auth_service
from app import deps, models


def _make_user_and_token(username="u1"):
    return auth_service.register(username, "pw", username)


def _make_project_with_leader(username="leader"):
    result = auth_service.register(username, "pw", "队长")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.add_project_member(pid, result["user"]["id"], "leader")
    return pid, result["token"], result["user"]["id"]


def test_get_current_user_valid_token():
    r = _make_user_and_token("u_valid")
    user = deps.get_current_user(r["token"])
    assert user["username"] == "u_valid"


def test_get_current_user_invalid_token_raises_401():
    with pytest.raises(HTTPException) as e:
        deps.get_current_user("invalid")
    assert e.value.status_code == 401


def test_get_current_user_none_token_raises_401():
    with pytest.raises(HTTPException) as e:
        deps.get_current_user(None)
    assert e.value.status_code == 401


def test_require_member_allowed():
    pid, token, uid = _make_project_with_leader("leader_m")
    user = deps.get_current_user(token)
    deps.require_member(pid, user)


def test_require_member_not_in_project_raises_403():
    r = auth_service.register("outsider", "pw", "外人")
    pid, _, _ = _make_project_with_leader("leader_x")
    user = deps.get_current_user(r["token"])
    with pytest.raises(HTTPException) as e:
        deps.require_member(pid, user)
    assert e.value.status_code == 403


def test_require_leader_leader_ok():
    pid, token, _ = _make_project_with_leader("leader_ok")
    user = deps.get_current_user(token)
    deps.require_leader(pid, user)


def test_require_leader_member_raises_403():
    pid, _, _ = _make_project_with_leader("leader_y")
    member = auth_service.register("mem_y", "pw", "队员")
    models.add_project_member(pid, member["user"]["id"], "member")
    user = deps.get_current_user(member["token"])
    with pytest.raises(HTTPException) as e:
        deps.require_leader(pid, user)
    assert e.value.status_code == 403
