import sys
from unittest.mock import MagicMock

# Mock weasyprint before importing main (which imports report, which imports weasyprint)
sys.modules['weasyprint'] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import main as app_module
from main import app

client = TestClient(app)


def test_get_root_returns_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_list_orgs_returns_list():
    with patch("main.auth.list_orgs", return_value=[]):
        resp = client.get("/orgs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_orgs_connect_returns_auth_url():
    with patch("main.auth.get_auth_url", return_value="https://login.salesforce.com/auth"):
        resp = client.post("/orgs/connect")
    assert resp.status_code == 200
    assert "auth_url" in resp.json()


def test_delete_org():
    with patch("main.auth.remove_org") as mock_remove:
        resp = client.delete("/orgs/org123")
    assert resp.status_code == 200
    mock_remove.assert_called_once_with("org123")


def test_scan_404_when_org_not_found():
    with patch("main.auth.get_org", return_value=None):
        resp = client.post("/scan", json={"org_id": "unknown"})
    assert resp.status_code == 404


def test_get_findings_returns_empty_when_no_scan():
    app_module._active_findings = []
    app_module._active_score = 100
    resp = client.get("/findings")
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data
    assert "score" in data


def test_report_404_when_no_findings():
    app_module._active_findings = None
    resp = client.post("/report", json={"client_name": "Acme"})
    assert resp.status_code == 404


def test_flows_describe_404_when_org_not_connected():
    app_module._active_org = None
    resp = client.post("/flows/Lead_Assignment/describe")
    assert resp.status_code == 404
