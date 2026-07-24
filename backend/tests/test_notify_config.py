"""项目级飞书 webhook 配置测试。"""
import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from app.services import auth_service, notify_service
from app import models, config


def _make_leader_and_project(username="leader"):
    r = auth_service.register(username, "pw", "队长")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.set_project_creator(pid, r["user"]["id"])
    models.add_project_member(pid, r["user"]["id"], "leader")
    return pid, r["token"], r["user"]["id"]


# ============ PATCH /api/projects/{pid} 权限与持久化 ============

def test_leader_can_update_project_notify_config():
    """队长 PATCH 成功，DB 字段更新。"""
    from app.routes import projects as projects_route

    pid, token, _ = _make_leader_and_project("leader_cfg")
    projects_route.update_project_notify_config(
        pid,
        projects_route.ProjectNotifyConfig(
            feishu_webhook_url="https://example.com/hook/project",
            feishu_secret="proj-secret"),
        authorization=f"Bearer {token}")

    project = models.get_project(pid)
    assert project["feishu_webhook_url"] == "https://example.com/hook/project"
    assert project["feishu_secret"] == "proj-secret"


def test_member_cannot_update_notify_config_returns_403():
    """队员 PATCH 返回 403。"""
    from app.routes import projects as projects_route

    pid, token, _ = _make_leader_and_project("leader_keep_cfg")
    member = auth_service.register("mem_cfg", "pw", "队员")
    models.add_project_member(pid, member["user"]["id"], "member")

    with pytest.raises(HTTPException) as e:
        projects_route.update_project_notify_config(
            pid,
            projects_route.ProjectNotifyConfig(feishu_webhook_url="x"),
            authorization=f"Bearer {member['token']}")
    assert e.value.status_code == 403


def test_update_notify_config_can_clear_fields():
    """队长可以用 null 清空已配置的 webhook。"""
    from app.routes import projects as projects_route

    pid, token, _ = _make_leader_and_project("leader_clear")
    # 先配置
    projects_route.update_project_notify_config(
        pid,
        projects_route.ProjectNotifyConfig(feishu_webhook_url="x", feishu_secret="y"),
        authorization=f"Bearer {token}")
    # 再清空
    projects_route.update_project_notify_config(
        pid,
        projects_route.ProjectNotifyConfig(feishu_webhook_url=None, feishu_secret=None),
        authorization=f"Bearer {token}")

    project = models.get_project(pid)
    assert project["feishu_webhook_url"] is None
    assert project["feishu_secret"] is None


# ============ send_feishu 项目级优先 + 全局兜底 ============

def test_send_feishu_uses_project_webhook_when_configured():
    """配置了项目级 webhook 时，send_feishu 用项目 URL。"""
    pid, _, _ = _make_leader_and_project("leader_send1")
    models.update_project_notify_config(
        pid, "https://example.com/hook/proj", "proj-secret")

    with patch("app.services.notify_service.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"StatusCode": 0})
        notify_service.send_feishu("test", project_id=pid, msg_type="manual_test")

    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    assert called_url == "https://example.com/hook/proj"


def test_send_feishu_falls_back_to_global_when_not_configured():
    """项目未配置 webhook 时，回退全局 .env。"""
    pid, _, _ = _make_leader_and_project("leader_send2")
    # 项目未配置 webhook
    original_url = config.FEISHU_WEBHOOK_URL
    original_secret = config.FEISHU_SECRET
    try:
        config.FEISHU_WEBHOOK_URL = "https://example.com/hook/global"
        config.FEISHU_SECRET = ""

        with patch("app.services.notify_service.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, json=lambda: {"StatusCode": 0})
            notify_service.send_feishu("test", project_id=pid, msg_type="manual_test")

        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        assert called_url == "https://example.com/hook/global"
    finally:
        config.FEISHU_WEBHOOK_URL = original_url
        config.FEISHU_SECRET = original_secret


def test_send_feishu_skips_when_neither_configured():
    """项目和全局都没配置时跳过推送（不发 httpx.post）。"""
    pid, _, _ = _make_leader_and_project("leader_send3")
    original_url = config.FEISHU_WEBHOOK_URL
    try:
        config.FEISHU_WEBHOOK_URL = ""
        with patch("app.services.notify_service.httpx.post") as mock_post:
            result = notify_service.send_feishu("test", project_id=pid, msg_type="manual_test")
        mock_post.assert_not_called()
        assert result["status"] == "failed"
    finally:
        config.FEISHU_WEBHOOK_URL = original_url
