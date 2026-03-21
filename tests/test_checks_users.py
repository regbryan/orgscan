import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from checks.users import check_inactive_users
from checks import Finding


def make_client(records):
    client = MagicMock()
    client.query.return_value = records
    return client


def days_ago(n):
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+0000")


def test_no_findings_when_all_users_active():
    records = [{"Name": "Alice", "Username": "a@b.com", "LastLoginDate": days_ago(10)}]
    client = make_client(records)
    findings = check_inactive_users(client)
    assert findings == []


def test_critical_finding_for_user_over_90_days():
    records = [{"Name": "Bob", "Username": "b@b.com", "LastLoginDate": days_ago(100)}]
    client = make_client(records)
    findings = check_inactive_users(client)
    assert len(findings) == 1
    assert findings[0].severity == "Critical"
    assert "Bob" in findings[0].detail


def test_user_with_null_last_login_is_flagged():
    records = [{"Name": "Carl", "Username": "c@b.com", "LastLoginDate": None}]
    client = make_client(records)
    findings = check_inactive_users(client)
    assert len(findings) == 1
    assert "Carl" in findings[0].detail


def test_multiple_inactive_users_produce_one_finding():
    records = [
        {"Name": "Dave", "Username": "d@b.com", "LastLoginDate": days_ago(200)},
        {"Name": "Eve", "Username": "e@b.com", "LastLoginDate": days_ago(150)},
    ]
    client = make_client(records)
    findings = check_inactive_users(client)
    assert len(findings) == 1
    assert "Dave" in findings[0].detail
    assert "Eve" in findings[0].detail


def test_finding_has_correct_category():
    records = [{"Name": "Frank", "Username": "f@b.com", "LastLoginDate": days_ago(95)}]
    findings = check_inactive_users(make_client(records))
    assert findings[0].category == "Users"
