import pytest
from unittest.mock import MagicMock, patch
from sf_client import SalesforceClient


@pytest.fixture
def org():
    return {
        "org_id": "org1",
        "access_token": "ACCESS_TOKEN",
        "instance_url": "https://test.salesforce.com",
        "refresh_token": "REFRESH_TOKEN",
    }


@pytest.fixture
def client(org):
    with patch("sf_client.Salesforce") as mock_sf:
        mock_instance = MagicMock()
        mock_sf.return_value = mock_instance
        c = SalesforceClient(org)
        c._sf = mock_instance
        return c


def test_query_returns_records(client):
    client._sf.query_all.return_value = {"records": [{"Id": "001", "Name": "Alice"}]}
    result = client.query("SELECT Id, Name FROM User")
    assert result == [{"Id": "001", "Name": "Alice"}]
    client._sf.query_all.assert_called_once_with("SELECT Id, Name FROM User")


def test_tooling_query_returns_records(client):
    client._sf.tooling.query.return_value = {"records": [{"Id": "301", "ApiVersion": 48}]}
    result = client.tooling_query("SELECT Id FROM FlowVersionView")
    assert result == [{"Id": "301", "ApiVersion": 48}]


def test_get_flow_xml_returns_xml_string(client):
    client._sf.tooling.query.return_value = {
        "records": [{"Metadata": {"processType": "Flow"}}]
    }
    result = client.get_flow_xml("Lead_Assignment")
    assert isinstance(result, str)


def test_write_flow_description_calls_tooling_update(client):
    # Mock the ID lookup
    client._sf.tooling.query.return_value = {"records": [{"Id": "300abc"}]}
    with patch.object(client, "tooling_update") as mock_update:
        client.write_flow_description("Lead_Assignment", "This flow assigns leads.")
        mock_update.assert_called_once_with(
            "FlowDefinition", "300abc", {"Description": "This flow assigns leads."}
        )


def test_tooling_update_makes_patch_request(client, org):
    with patch("sf_client.requests.patch") as mock_patch:
        mock_patch.return_value = MagicMock(status_code=204)
        mock_patch.return_value.raise_for_status = MagicMock()
        client.tooling_update("FlowDefinition", "300abc", {"Description": "test"})
        mock_patch.assert_called_once()
        call_url = mock_patch.call_args[0][0]
        assert "FlowDefinition/300abc" in call_url
