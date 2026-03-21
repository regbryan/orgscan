import json
import re
import requests
from simple_salesforce import Salesforce

API_VERSION = "59.0"
_SAFE_DEV_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


def _validate_dev_name(name: str) -> str:
    """Raise ValueError if name is not a valid Salesforce DeveloperName."""
    if not _SAFE_DEV_NAME.match(name):
        raise ValueError(f"Invalid DeveloperName: {name!r}")
    return name


class SalesforceClient:
    """Wrapper around simple-salesforce for REST, Tooling, and description writes."""

    def __init__(self, org: dict):
        self._org = org
        self._sf = Salesforce(
            instance_url=org["instance_url"],
            session_id=org["access_token"],
            version=API_VERSION,
        )

    def query(self, soql: str) -> list[dict]:
        """Run a SOQL query via REST API. Returns list of record dicts."""
        result = self._sf.query_all(soql)
        return result.get("records", [])

    def tooling_query(self, soql: str) -> list[dict]:
        """Run a SOQL query via Tooling API. Returns list of record dicts."""
        result = self._sf.tooling.query(soql)
        return result.get("records", [])

    def get_flow_xml(self, flow_api_name: str) -> str:
        """Retrieve the full flow definition metadata for a flow by its DeveloperName.
        Returns a JSON string (simple-salesforce deserializes the Metadata field to a dict)."""
        _validate_dev_name(flow_api_name)
        records = self.tooling_query(
            f"SELECT Metadata FROM FlowDefinition WHERE DeveloperName = '{flow_api_name}'"
        )
        if not records:
            raise ValueError(f"Flow not found: {flow_api_name}")
        metadata = records[0].get("Metadata", {})
        # Metadata is returned as a dict by simple-salesforce; serialize to JSON string
        return json.dumps(metadata, indent=2)

    def write_flow_description(self, flow_api_name: str, description: str) -> None:
        """Write a description back to a Salesforce flow via Tooling API PATCH."""
        _validate_dev_name(flow_api_name)
        records = self.tooling_query(
            f"SELECT Id FROM FlowDefinition WHERE DeveloperName = '{flow_api_name}'"
        )
        if not records:
            raise ValueError(f"Flow not found: {flow_api_name}")
        flow_id = records[0]["Id"]
        self.tooling_update("FlowDefinition", flow_id, {"Description": description})

    def tooling_update(self, sobject: str, record_id: str, data: dict) -> None:
        """PATCH a Tooling API record."""
        url = f"{self._org['instance_url']}/services/data/v{API_VERSION}/tooling/sobjects/{sobject}/{record_id}"
        headers = {
            "Authorization": f"Bearer {self._org['access_token']}",
            "Content-Type": "application/json",
        }
        resp = requests.patch(url, headers=headers, json=data)
        resp.raise_for_status()
