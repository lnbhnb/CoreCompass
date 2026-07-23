import pytest
from unittest.mock import patch, MagicMock
from app.llm import client
from app.llm.client import parse_json_robust, LLMUnavailableError


def test_parse_json_robust_plain():
    assert parse_json_robust('{"a": 1}') == {"a": 1}


def test_parse_json_robust_with_codeblock():
    assert parse_json_robust('```json\n{"a": 2}\n```') == {"a": 2}


def test_parse_json_robust_with_trailing_comma():
    assert parse_json_robust('{"a": 1,}') == {"a": 1}


def test_call_llm_success():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    with patch.object(client, "get_client", return_value=MagicMock(
        chat=MagicMock(completions=MagicMock(create=MagicMock(return_value=mock_resp))))):
        assert client.call_llm("test") == {"ok": True}


def test_call_llm_retry_then_fail():
    with patch.object(client, "get_client", return_value=MagicMock(
        chat=MagicMock(completions=MagicMock(create=MagicMock(side_effect=Exception("net")))))):
        with patch.object(client.time, "sleep"):
            with pytest.raises(LLMUnavailableError):
                client.call_llm("test", max_retries=1)


def test_generate_initial_plan_fallback():
    with patch.object(client, "call_llm", side_effect=LLMUnavailableError("down")):
        result = client.generate_initial_plan("topic", 3, "2026-08-01")
        assert "milestones" in result and len(result["milestones"]) >= 3
