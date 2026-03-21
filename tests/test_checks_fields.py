import pytest
from unittest.mock import MagicMock
from checks.fields import check_unused_fields
from checks import Finding


def make_client(records):
    client = MagicMock()
    client.tooling_query.return_value = records
    return client


def make_field(name="My_Field__c", sobject="Account", populated_count=0, total_count=100):
    return {
        "DeveloperName": name,
        "EntityDefinition": {"QualifiedApiName": sobject},
        "PopulatedCount": populated_count,
        "TotalCount": total_count,
    }


def test_no_findings_when_all_fields_populated():
    client = make_client([make_field(populated_count=50)])
    assert check_unused_fields(client) == []


def test_warning_finding_for_zero_population():
    client = make_client([make_field(populated_count=0, total_count=100)])
    findings = check_unused_fields(client)
    assert len(findings) == 1
    assert findings[0].severity == "Warning"


def test_no_finding_when_no_records_exist():
    client = make_client([make_field(populated_count=0, total_count=0)])
    assert check_unused_fields(client) == []


def test_finding_contains_field_and_object_name():
    client = make_client([make_field(name="Custom_Score__c", sobject="Lead", populated_count=0, total_count=200)])
    findings = check_unused_fields(client)
    assert "Custom_Score__c" in findings[0].detail
    assert "Lead" in findings[0].detail


def test_finding_category_is_fields():
    client = make_client([make_field(populated_count=0, total_count=10)])
    assert check_unused_fields(client)[0].category == "Fields"
