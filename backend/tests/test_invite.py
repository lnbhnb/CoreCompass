import pytest
from datetime import datetime, timedelta
from app.services import auth_service, member_service
from app import models


def _setup_leader_and_project(username="leader"):
    r = auth_service.register(username, "pw", "队长")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.set_project_creator(pid, r["user"]["id"])
    models.add_project_member(pid, r["user"]["id"], "leader")
    return pid, r["user"]["id"], r["token"]


def test_generate_invite_returns_6char_code():
    pid, _, token = _setup_leader_and_project("l1")
    result = member_service.generate_invite(pid, token)
    assert len(result["code"]) == 6
    assert result["code"].isupper()


def test_member_joins_with_valid_code():
    pid, _, leader_token = _setup_leader_and_project("l2")
    inv = member_service.generate_invite(pid, leader_token)
    member = auth_service.register("mem2", "pw", "队员")
    member_service.join_with_code(inv["code"], member["token"])
    m = models.get_project_member(pid, member["user"]["id"])
    assert m["role"] == "member"


def test_used_code_cannot_reuse():
    pid, _, leader_token = _setup_leader_and_project("l3")
    inv = member_service.generate_invite(pid, leader_token)
    m1 = auth_service.register("m3a", "pw", "队员A")
    member_service.join_with_code(inv["code"], m1["token"])
    m2 = auth_service.register("m3b", "pw", "队员B")
    with pytest.raises(ValueError, match="邀请码"):
        member_service.join_with_code(inv["code"], m2["token"])


def test_expired_code_raises():
    pid, _, leader_token = _setup_leader_and_project("l4")
    expires = (datetime.now() - timedelta(days=1)).isoformat()
    models.create_invite(pid, "OLDCOD", expires)
    member = auth_service.register("m4", "pw", "队员")
    with pytest.raises(ValueError, match="过期"):
        member_service.join_with_code("OLDCOD", member["token"])


def test_unknown_code_raises():
    member = auth_service.register("m5", "pw", "队员")
    with pytest.raises(ValueError, match="邀请码"):
        member_service.join_with_code("NOPE00", member["token"])


def test_join_already_member_idempotent():
    """队员已是成员，再次用码加入不应重复插入（UNIQUE 约束）。"""
    pid, _, leader_token = _setup_leader_and_project("l6")
    inv = member_service.generate_invite(pid, leader_token)
    member = auth_service.register("m6", "pw", "队员")
    member_service.join_with_code(inv["code"], member["token"])
    # 第二次用新码加入同项目
    inv2 = member_service.generate_invite(pid, leader_token)
    # 已是成员，应幂等成功或抛错——这里期望幂等成功
    result = member_service.join_with_code(inv2["code"], member["token"])
    assert result["project_id"] == pid
