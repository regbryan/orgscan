import pytest
from unittest.mock import MagicMock
from checks.activity import get_activity_log, get_activity_findings, ActivityEvent


def make_client(login_records=None, audit_records=None, raise_on_login=False, raise_on_audit=False):
    client = MagicMock()

    call_count = [0]

    def query_side_effect(soql):
        call_count[0] += 1
        if "LoginHistory" in soql:
            if raise_on_login:
                raise Exception("Login query failed")
            return login_records or []
        if "SetupAuditTrail" in soql:
            if raise_on_audit:
                raise Exception("Audit query failed")
            return audit_records or []
        return []

    client.query.side_effect = query_side_effect
    return client


def test_get_activity_log_returns_login_events():
    login_records = [
        {
            "UserId": "005xx000001",
            "Username": "alice@example.com",
            "LoginTime": "2025-03-10T10:00:00Z",
            "SourceIp": "1.2.3.4",
            "Status": "Success",
            "LoginType": "Application",
        }
    ]
    client = make_client(login_records=login_records)
    events = get_activity_log(client, days=30)

    login_events = [e for e in events if e.event_type == "Login"]
    assert len(login_events) == 1
    e = login_events[0]
    assert e.event_type == "Login"
    assert e.user == "alice@example.com"
    assert e.action == "Application login"
    assert e.timestamp == "2025-03-10T10:00:00Z"
    assert e.ip_address == "1.2.3.4"
    assert e.status == "Success"


def test_get_activity_log_returns_setup_events():
    audit_records = [
        {
            "CreatedByContext": None,
            "CreatedDate": "2025-03-12T09:00:00Z",
            "Action": "permSetGroupCreate",
            "Section": "Permission Set Groups",
            "Display": "Created permission set group MyGroup",
            "CreatedBy": {"Username": "admin@example.com"},
        }
    ]
    client = make_client(audit_records=audit_records)
    events = get_activity_log(client, days=30)

    setup_events = [e for e in events if e.event_type == "Setup Change"]
    assert len(setup_events) == 1
    e = setup_events[0]
    assert e.event_type == "Setup Change"
    assert e.user == "admin@example.com"
    assert e.action == "Created permission set group MyGroup"
    assert e.timestamp == "2025-03-12T09:00:00Z"
    assert e.ip_address == ""
    assert e.status == "Warning"


def test_get_activity_findings_flags_repeated_failed_logins():
    # 5 failed logins for the same user => Critical finding
    login_records = [
        {
            "Username": "badactor@example.com",
            "LoginTime": f"2025-03-{10+i:02d}T10:00:00Z",
            "SourceIp": "9.9.9.9",
            "Status": "Failed",
            "LoginType": "Application",
        }
        for i in range(5)
    ]
    client = make_client(login_records=login_records)
    findings = get_activity_findings(client)

    critical = [f for f in findings if f.severity == "Critical" and f.category == "Activity"]
    assert len(critical) == 1
    assert "badactor@example.com" in critical[0].detail
    assert "5 failures" in critical[0].detail


def test_get_activity_findings_flags_high_setup_volume():
    # 21 setup audit events => Warning finding
    audit_records = [
        {
            "CreatedDate": f"2025-03-{(i % 28) + 1:02d}T10:00:00Z",
            "Action": "someChange",
            "Section": "Security",
            "Display": f"Change number {i}",
            "CreatedBy": {"Username": "admin@example.com"},
        }
        for i in range(21)
    ]
    client = make_client(audit_records=audit_records)
    findings = get_activity_findings(client)

    warnings = [f for f in findings if f.severity == "Warning" and f.category == "Activity"]
    assert len(warnings) == 1
    assert "21" in warnings[0].title


def test_get_activity_log_handles_query_exception():
    # Both queries raise — should return empty list, not crash
    client = make_client(raise_on_login=True, raise_on_audit=True)
    events = get_activity_log(client, days=30)
    assert events == []
