import pytest
from app.services import auth_service, review_service
from app import models


def _setup_project_with_leader_and_member(prefix="r"):
    leader = auth_service.register(f"{prefix}_leader", "pw", "队长")
    member = auth_service.register(f"{prefix}_member", "pw", "队员")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.set_project_creator(pid, leader["user"]["id"])
    models.add_project_member(pid, leader["user"]["id"], "leader")
    models.add_project_member(pid, member["user"]["id"], "member")
    mid = models.create_milestone(pid, "M1", 0, "md")
    tid = models.create_task(mid, pid, "T1", "", "optional", "mid", 1.0, None, None)
    return pid, mid, tid, leader, member


def test_leader_assigns_task_to_member():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("a")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    task = models.get_task(tid)
    assert task["assignee_id"] == member["user"]["id"]


def test_member_cannot_assign():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("b")
    with pytest.raises(PermissionError, match="队长"):
        review_service.assign_task(tid, member["user"]["id"], member["token"], pid)


def test_member_claims_unassigned_task():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("c")
    review_service.claim_task(tid, member["token"], pid)
    task = models.get_task(tid)
    assert task["assignee_id"] == member["user"]["id"]


def test_claim_already_assigned_raises():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("c2")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    other = auth_service.register("c2_other", "pw", "其他人")
    models.add_project_member(pid, other["user"]["id"], "member")
    with pytest.raises(ValueError, match="已被认领"):
        review_service.claim_task(tid, other["token"], pid)


def test_member_submits_and_leader_approves(tmp_path):
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("d")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    f = tmp_path / "demo.md"
    f.write_text("# demo\ncontent")
    review_service.submit_task(tid, "demo.md", str(f), member["token"], pid)
    task = models.get_task(tid)
    assert task["review_status"] == "pending_review"
    review_service.review_task(tid, "approved", leader["token"], pid, "做得好")
    task = models.get_task(tid)
    assert task["review_status"] == "approved"
    assert task["review_comment"] == "做得好"


def test_member_cannot_review():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("e")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    with pytest.raises(PermissionError, match="队长"):
        review_service.review_task(tid, "approved", member["token"], pid)


def test_non_assignee_cannot_submit(tmp_path):
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("f")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    other = auth_service.register("f_other", "pw", "其他人")
    models.add_project_member(pid, other["user"]["id"], "member")
    f = tmp_path / "x.md"
    f.write_text("x")
    with pytest.raises(PermissionError, match="负责人"):
        review_service.submit_task(tid, "x.md", str(f), other["token"], pid)


def test_review_states_transition():
    from app.state_machine import ReviewStatus, transition_review, InvalidTransition
    assert transition_review(None, "submit") == ReviewStatus.PENDING
    assert transition_review(ReviewStatus.PENDING, "approve") == ReviewStatus.APPROVED
    assert transition_review(ReviewStatus.PENDING, "reject") == ReviewStatus.REJECTED
    assert transition_review(ReviewStatus.REJECTED, "resubmit") == ReviewStatus.PENDING
    with pytest.raises(InvalidTransition):
        transition_review(ReviewStatus.APPROVED, "submit")


def test_submit_triggers_leader_notification(tmp_path):
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("g")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    f = tmp_path / "demo.md"
    f.write_text("x")
    review_service.submit_task(tid, "demo.md", str(f), member["token"], pid)
    notifs = models.list_notifications(pid)
    assert any(n["type"] == "task_submit" for n in notifs)
