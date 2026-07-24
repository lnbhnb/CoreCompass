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


# ============ 删除项目 ============

def _make_project_with_tasks(username="leader"):
    """建一个带里程碑+任务的完整项目，用于验证级联删除。"""
    pid, token, uid = _make_project_with_leader(username)
    mid = models.create_milestone(pid, "M1", 0, "other")
    models.create_task(
        milestone_id=mid, project_id=pid, title="T1", description="",
        priority="optional", difficulty="mid", est_effort_days=1.0,
        start_date="2026-07-24", due_date="2026-07-31")
    return pid, token, uid, mid


def test_leader_can_delete_project_and_cascade():
    """队长删除项目后，项目、里程碑、任务、成员关系全部消失。"""
    pid, token, uid, mid = _make_project_with_tasks("leader_del")
    models.delete_project(pid)

    assert models.get_project(pid) is None
    assert models.list_milestones(pid) == []
    assert models.list_tasks_by_project(pid, include_cut=True) == []
    assert models.get_project_member(pid, uid) is None
    assert models.list_project_members(pid) == []


def test_member_cannot_delete_project_returns_403():
    """队员调用删除 → 403。"""
    from app.routes import projects as projects_route

    pid, leader_token, _ = _make_project_with_leader("leader_keep")
    member = auth_service.register("mem_del", "pw", "队员")
    models.add_project_member(pid, member["user"]["id"], "member")

    with pytest.raises(HTTPException) as e:
        projects_route.delete_project(pid, authorization=f"Bearer {member['token']}")
    assert e.value.status_code == 403
    # 项目仍在
    assert models.get_project(pid) is not None


def test_non_member_cannot_delete_project_returns_403():
    """非项目成员调用删除 → 403。"""
    from app.routes import projects as projects_route

    pid, _, _ = _make_project_with_leader("leader_keep2")
    outsider = auth_service.register("out_del", "pw", "外人")

    with pytest.raises(HTTPException) as e:
        projects_route.delete_project(pid, authorization=f"Bearer {outsider['token']}")
    assert e.value.status_code == 403
    assert models.get_project(pid) is not None


def test_leader_delete_project_via_api_succeeds():
    """队长通过 API 删除项目返回 200，项目消失。"""
    from app.routes import projects as projects_route

    pid, token, uid, mid = _make_project_with_tasks("leader_api")
    result = projects_route.delete_project(pid, authorization=f"Bearer {token}")
    assert result == {"deleted": pid}
    assert models.get_project(pid) is None
