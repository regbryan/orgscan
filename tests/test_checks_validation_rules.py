import pytest
from unittest.mock import MagicMock
from checks.validation_rules import check_validation_rules
from checks import Finding


def make_client(records):
    client = MagicMock()
    client.tooling_query.return_value = records
    return client


def make_rule(name="Rule1", sobject="Account", description="Has description", active=True):
    return {
        "ValidationName": name,
        "EntityDefinition": {"QualifiedApiName": sobject},
        "Description": description,
        "Active": active,
    }


def test_no_findings_for_described_rule():
    assert check_validation_rules(make_client([make_rule()])) == []


def test_info_finding_for_rule_without_description():
    findings = check_validation_rules(make_client([make_rule(description=None)]))
    assert len(findings) == 1
    assert findings[0].severity == "Info"


def test_inactive_rules_are_ignored():
    assert check_validation_rules(make_client([make_rule(description=None, active=False)])) == []


def test_finding_contains_rule_and_object():
    findings = check_validation_rules(make_client([make_rule(name="CheckBudget", sobject="Opportunity", description="")]))
    assert "CheckBudget" in findings[0].detail
    assert "Opportunity" in findings[0].detail


def test_finding_category_is_validation():
    findings = check_validation_rules(make_client([make_rule(description=None)]))
    assert findings[0].category == "Validation"
