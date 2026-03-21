import pytest
from unittest.mock import MagicMock
from checks.flows import check_flows
from checks import Finding


def make_client(records):
    client = MagicMock()
    client.tooling_query.return_value = records
    return client


def make_flow(name="TestFlow", api_version=59, description="A description", formulas=None):
    return {
        "DeveloperName": name,
        "ApiVersion": api_version,
        "Description": description,
        "ProcessType": "Flow",
        "Metadata": {"formulas": formulas or []},
    }


def test_no_findings_for_clean_flow():
    client = make_client([make_flow()])
    findings = check_flows(client)
    assert findings == []


def test_critical_finding_for_old_api_version():
    client = make_client([make_flow(api_version=48)])
    findings = check_flows(client)
    severities = [f.severity for f in findings]
    assert "Critical" in severities
    titles = [f.title for f in findings]
    assert any("API version" in t for t in titles)


def test_warning_finding_for_missing_description():
    client = make_client([make_flow(description=None)])
    findings = check_flows(client)
    assert any(f.severity == "Warning" and "description" in f.title.lower() for f in findings)


def test_warning_finding_for_empty_description():
    client = make_client([make_flow(description="")])
    findings = check_flows(client)
    assert any("description" in f.title.lower() for f in findings)


def test_flow_api_name_set_on_description_finding():
    client = make_client([make_flow(name="Lead_Assignment", description="")])
    findings = check_flows(client)
    desc_finding = next(f for f in findings if "description" in f.title.lower())
    assert desc_finding.flow_api_name == "Lead_Assignment"


def test_warning_for_hardcoded_id_in_formula():
    formula = {"expression": "Id == '0013000000AbCdEf012'"}
    client = make_client([make_flow(formulas=[formula])])
    findings = check_flows(client)
    assert any("hard-coded" in f.title.lower() for f in findings)


def test_no_hardcoded_id_false_positive():
    formula = {"expression": "Name == 'Test'"}
    client = make_client([make_flow(formulas=[formula])])
    findings = check_flows(client)
    assert not any("hard-coded" in f.title.lower() for f in findings)
