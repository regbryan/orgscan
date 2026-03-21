import json
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import auth


@pytest.fixture(autouse=True)
def tmp_tokens(tmp_path, monkeypatch):
    tokens_file = tmp_path / "tokens.json"
    monkeypatch.setattr(auth, "TOKENS_FILE", tokens_file)
    return tokens_file


@pytest.fixture(autouse=True)
def clear_pending_verifiers():
    auth._pending_verifiers.clear()
    yield
    auth._pending_verifiers.clear()


def test_get_auth_url_contains_client_id(monkeypatch):
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "MY_CLIENT_ID")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8000")
    url = auth.get_auth_url(state="abc123")
    assert "MY_CLIENT_ID" in url
    assert "abc123" in url
    assert "login.salesforce.com" in url
    assert "code_challenge" in url


def test_get_auth_url_stores_verifier(monkeypatch):
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "MY_CLIENT_ID")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8000")
    url = auth.get_auth_url(state="teststate")
    assert "teststate" in auth._pending_verifiers
    assert len(auth._pending_verifiers["teststate"]) > 0


def test_exchange_code_sends_verifier(monkeypatch):
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "MY_CLIENT_ID")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "MY_SECRET")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8000")
    auth._pending_verifiers["mystate"] = "my_test_verifier"

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "tok", "instance_url": "https://x.sf.com"}
    mock_response.raise_for_status = MagicMock()

    with patch("auth.requests.post", return_value=mock_response) as mock_post:
        auth.exchange_code("mycode", state="mystate")
        call_kwargs = mock_post.call_args
        posted_data = call_kwargs[1]["data"] if "data" in call_kwargs[1] else call_kwargs[0][1]
        assert "code_verifier" in posted_data
        assert posted_data["code_verifier"] == "my_test_verifier"


def test_load_tokens_returns_empty_when_no_file():
    tokens = auth.load_tokens()
    assert tokens == {}


def test_save_and_load_tokens(tmp_tokens):
    data = {"org1": {"access_token": "tok", "refresh_token": "ref", "instance_url": "https://x.sf.com"}}
    auth.save_tokens(data)
    loaded = auth.load_tokens()
    assert loaded == data


def test_get_org_returns_none_when_not_found():
    assert auth.get_org("nonexistent") is None


def test_get_org_returns_org_data(tmp_tokens):
    data = {"org1": {"access_token": "tok", "instance_url": "https://x.sf.com"}}
    auth.save_tokens(data)
    org = auth.get_org("org1")
    assert org["access_token"] == "tok"


def test_remove_org(tmp_tokens):
    data = {"org1": {"access_token": "tok"}, "org2": {"access_token": "tok2"}}
    auth.save_tokens(data)
    auth.remove_org("org1")
    tokens = auth.load_tokens()
    assert "org1" not in tokens
    assert "org2" in tokens


def test_list_orgs(tmp_tokens):
    data = {
        "org1": {"access_token": "tok", "username": "a@b.com", "instance_url": "https://x.sf.com"},
        "org2": {"access_token": "tok2", "username": "c@d.com", "instance_url": "https://y.sf.com"},
    }
    auth.save_tokens(data)
    orgs = auth.list_orgs()
    assert len(orgs) == 2
    assert all("org_id" in o for o in orgs)
