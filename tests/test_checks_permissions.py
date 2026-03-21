import pytest
from unittest.mock import MagicMock
from checks.permissions import check_excessive_permissions
from checks import Finding


def make_client(records):
    client = MagicMock()
    client.query.return_value = records
    return client


def test_no_findings_for_restricted_profile():
    records = [{"Name": "Standard User", "PermissionsModifyAllData": False, "PermissionsViewAllData": False}]
    assert check_excessive_permissions(make_client(records)) == []


def test_critical_finding_for_modify_all():
    records = [{"Name": "Sales Rep", "PermissionsModifyAllData": True, "PermissionsViewAllData": False}]
    findings = check_excessive_permissions(make_client(records))
    assert len(findings) == 1
    assert findings[0].severity == "Critical"
    assert "Sales Rep" in findings[0].detail


def test_critical_finding_for_view_all():
    records = [{"Name": "Read Only", "PermissionsModifyAllData": False, "PermissionsViewAllData": True}]
    findings = check_excessive_permissions(make_client(records))
    assert len(findings) == 1


def test_multiple_dangerous_profiles():
    records = [
        {"Name": "Profile A", "PermissionsModifyAllData": True, "PermissionsViewAllData": False},
        {"Name": "Profile B", "PermissionsModifyAllData": False, "PermissionsViewAllData": True},
    ]
    findings = check_excessive_permissions(make_client(records))
    assert len(findings) == 2


def test_finding_category_is_permissions():
    records = [{"Name": "Admin", "PermissionsModifyAllData": True, "PermissionsViewAllData": False}]
    findings = check_excessive_permissions(make_client(records))
    assert findings[0].category == "Permissions"
