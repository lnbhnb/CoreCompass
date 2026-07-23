import pytest
from unittest.mock import patch, MagicMock
from app.services import notify_service
from app import models, config


def test_send_feishu_no_webhook_configured(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_WEBHOOK_URL", "")
    result = notify_service.send_feishu("test", project_id=None)
    assert result["status"] == "failed"
    assert models.list_notifications(limit=1)[0]["status"] == "failed"


def test_send_feishu_success(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_WEBHOOK_URL", "https://example.com/hook")
    monkeypatch.setattr(config, "FEISHU_SECRET", "")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"StatusCode": 0, "msg": "ok"}
    with patch("app.services.notify_service.httpx.post", return_value=mock_resp):
        result = notify_service.send_feishu("hello", project_id=None)
    assert result["status"] == "sent"
    assert models.list_notifications(limit=1)[0]["status"] == "sent"


def test_send_feishu_network_error(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_WEBHOOK_URL", "https://example.com/hook")
    with patch("app.services.notify_service.httpx.post", side_effect=Exception("timeout")):
        result = notify_service.send_feishu("hello", project_id=None)
    assert result["status"] == "failed"
