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


def _is_session_expired(exc: Exception) -> bool:
    """Return True when the exception indicates an expired/invalid Salesforce session."""
    msg = str(exc).lower()
    return (
        "invalid_session_id" in msg
        or "session expired" in msg
        or "401 client error" in msg
        or "unauthorized" in msg
    )


class SalesforceClient:
    """Wrapper around simple-salesforce with automatic token refresh on session expiry."""

    def __init__(self, org: dict):
        self._org = org
        self._sf = self._build_sf()

    def _build_sf(self) -> Salesforce:
        return Salesforce(
            instance_url=self._org["instance_url"],
            session_id=self._org["access_token"],
            version=API_VERSION,
        )

    def _refresh(self) -> None:
        """Call auth.refresh_access_token, update the stored token, rebuild the SF client."""
        import auth
        org_id = self._org.get("org_id")
        if not org_id:
            raise RuntimeError("Cannot refresh token: org_id missing from org dict")
        updated = auth.refresh_access_token(org_id)
        # Merge refreshed fields back into _org
        self._org = {**self._org, **updated}
        self._sf = self._build_sf()

    @property
    def instance_url(self) -> str:
        return self._org.get("instance_url", "")

    def sf_url(self, path: str) -> str:
        """Build a full Salesforce URL from a relative Setup/Lightning path."""
        return self.instance_url + path

    # ── Public API ───────────────────────────────────────────────────────────

    def query(self, soql: str) -> list[dict]:
        """Run a SOQL query via REST API. Auto-refreshes once on session expiry."""
        try:
            return self._sf.query_all(soql).get("records", [])
        except Exception as e:
            if _is_session_expired(e):
                self._refresh()
                return self._sf.query_all(soql).get("records", [])
            raise

    def tooling_query(self, soql: str) -> list[dict]:
        """Run a SOQL query via Tooling API. Auto-refreshes once on session expiry."""
        try:
            return self._tooling_get(soql)
        except Exception as e:
            if _is_session_expired(e):
                self._refresh()
                return self._tooling_get(soql)
            raise

    def _tooling_get(self, soql: str) -> list[dict]:
        url = f"{self._org['instance_url']}/services/data/v{API_VERSION}/tooling/query/"
        headers = {"Authorization": f"Bearer {self._org['access_token']}"}
        resp = requests.get(url, headers=headers, params={"q": soql})
        resp.raise_for_status()
        return resp.json().get("records", [])

    def get_flow_xml(self, flow_api_name: str) -> str:
        """Retrieve the full flow version metadata (nodes, connectors, etc.) by DeveloperName."""
        _validate_dev_name(flow_api_name)

        # Step 1: Get the ActiveVersionId from FlowDefinition
        defs = self.tooling_query(
            f"SELECT ActiveVersionId FROM FlowDefinition WHERE DeveloperName = '{flow_api_name}'"
        )
        if not defs:
            raise ValueError(f"Flow not found: {flow_api_name}")

        active_version_id = defs[0].get("ActiveVersionId")
        if not active_version_id:
            raise ValueError(f"Flow {flow_api_name} has no active version")

        # Step 2: Fetch the full Flow version record with all elements
        try:
            versions = self.tooling_query(
                f"SELECT FullName, Metadata FROM Flow WHERE Id = '{active_version_id}'"
            )
            if versions and versions[0].get("Metadata"):
                metadata = versions[0]["Metadata"]
                # Trim large binary/null sections to stay within AI token limits
                if isinstance(metadata, dict):
                    for key in list(metadata.keys()):
                        val = metadata[key]
                        if val is None or val == [] or val == {}:
                            del metadata[key]
                return json.dumps(metadata, indent=2)
        except Exception:
            pass  # Fall back to REST metadata endpoint

        # Step 3: Fallback — use the REST Composite API for flow definition body
        try:
            flow_data = self.rest_get(f"tooling/sobjects/Flow/{active_version_id}")
            if flow_data and flow_data.get("Metadata"):
                metadata = flow_data["Metadata"]
                if isinstance(metadata, dict):
                    for key in list(metadata.keys()):
                        val = metadata[key]
                        if val is None or val == [] or val == {}:
                            del metadata[key]
                return json.dumps(metadata, indent=2)
        except Exception:
            pass

        # Step 4: Last resort — return FlowDefinition-level metadata
        defs2 = self.tooling_query(
            f"SELECT Metadata FROM FlowDefinition WHERE DeveloperName = '{flow_api_name}'"
        )
        metadata = defs2[0].get("Metadata", {}) if defs2 else {}
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
        """PATCH a Tooling API record. Auto-refreshes once on session expiry."""
        try:
            self._tooling_patch(sobject, record_id, data)
        except Exception as e:
            if _is_session_expired(e):
                self._refresh()
                self._tooling_patch(sobject, record_id, data)
            else:
                raise

    def delete_record(self, object_name: str, record_id: str) -> None:
        """Delete a standard Salesforce record by Id. Auto-refreshes once on session expiry."""
        try:
            getattr(self._sf, object_name).delete(record_id)
        except Exception as e:
            if _is_session_expired(e):
                self._refresh()
                getattr(self._sf, object_name).delete(record_id)
            else:
                raise

    def rest_get(self, path: str) -> dict:
        """GET a data REST API endpoint. Returns parsed JSON. Auto-refreshes on session expiry."""
        try:
            return self._rest_fetch(path)
        except Exception as e:
            if _is_session_expired(e):
                self._refresh()
                return self._rest_fetch(path)
            raise

    def _rest_fetch(self, path: str) -> dict:
        url = f"{self._org['instance_url']}/services/data/v{API_VERSION}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self._org['access_token']}"}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def _tooling_patch(self, sobject: str, record_id: str, data: dict) -> None:
        url = (
            f"{self._org['instance_url']}/services/data/v{API_VERSION}"
            f"/tooling/sobjects/{sobject}/{record_id}"
        )
        headers = {
            "Authorization": f"Bearer {self._org['access_token']}",
            "Content-Type": "application/json",
        }
        resp = requests.patch(url, headers=headers, json=data)
        resp.raise_for_status()
