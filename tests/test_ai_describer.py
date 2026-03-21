import pytest
from unittest.mock import patch, MagicMock
from checks import Finding
import ai_describer


def make_mock_claude(text):
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    mock_client.messages.create.return_value = mock_msg
    return mock_client


def test_generate_flow_description_returns_string(monkeypatch):
    mock_client = make_mock_claude("This flow assigns leads based on territory.")
    monkeypatch.setattr(ai_describer, "_client", mock_client)
    result = ai_describer.generate_flow_description("<Flow>...</Flow>")
    assert result == "This flow assigns leads based on territory."


def test_generate_flow_description_calls_claude_with_xml(monkeypatch):
    mock_client = make_mock_claude("desc")
    monkeypatch.setattr(ai_describer, "_client", mock_client)
    ai_describer.generate_flow_description("<Flow>test xml</Flow>")
    call_args = mock_client.messages.create.call_args
    # XML should appear in the user message
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert any("test xml" in str(m) for m in messages)


def test_generate_org_narrative_returns_string(monkeypatch):
    mock_client = make_mock_claude("The org has moderate health issues.")
    monkeypatch.setattr(ai_describer, "_client", mock_client)
    findings = [Finding("Users", "Critical", "t", "d", "r")]
    result = ai_describer.generate_org_narrative(findings, score=72)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_org_narrative_includes_score_in_prompt(monkeypatch):
    mock_client = make_mock_claude("ok")
    monkeypatch.setattr(ai_describer, "_client", mock_client)
    ai_describer.generate_org_narrative([], score=55)
    call_args = mock_client.messages.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert any("55" in str(m) for m in messages)
