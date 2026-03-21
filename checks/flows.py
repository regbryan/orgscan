import re
from checks import Finding

SOQL = (
    "SELECT DeveloperName, ApiVersion, Description, ProcessType, Metadata "
    "FROM FlowDefinition WHERE Status = 'Active'"
)
MIN_API_VERSION = 50
SF_ID_PATTERN = re.compile(r"'0[a-zA-Z0-9]{14,18}'")


def check_flows(sf_client) -> list[Finding]:
    records = sf_client.tooling_query(SOQL)
    findings = []

    old_api = [r for r in records if (r.get("ApiVersion") or 0) < MIN_API_VERSION]
    if old_api:
        names = ", ".join(r["DeveloperName"] for r in old_api)
        findings.append(Finding(
            category="Flows",
            severity="Critical",
            title=f"{len(old_api)} flow(s) running on API version < {MIN_API_VERSION}",
            detail=f"Flows: {names}",
            recommendation="Upgrade these flows to API version 59.0 in the Flow Builder.",
        ))

    no_desc = [r for r in records if not r.get("Description")]
    if no_desc:
        findings.extend(
            Finding(
                category="Flows",
                severity="Warning",
                title=f"Flow has no description",
                detail=f"{r['DeveloperName']} has no description",
                recommendation="Generate a description with AI using the button below.",
                flow_api_name=r["DeveloperName"],
            )
            for r in no_desc
        )

    for r in records:
        metadata = r.get("Metadata") or {}
        formulas = metadata.get("formulas") or []
        for formula in formulas:
            expr = formula.get("expression", "")
            if SF_ID_PATTERN.search(expr):
                findings.append(Finding(
                    category="Flows",
                    severity="Warning",
                    title="Hard-coded record ID in flow formula",
                    detail=f"{r['DeveloperName']}: {expr[:120]}",
                    recommendation="Replace hard-coded IDs with Custom Labels or Custom Metadata.",
                    flow_api_name=r["DeveloperName"],
                ))
                break

    return findings
