from checks import Finding

SOQL = (
    "SELECT ValidationName, EntityDefinition.QualifiedApiName, Description, Active "
    "FROM ValidationRule "
    "WHERE Active = true"
)


def check_validation_rules(sf_client) -> list[Finding]:
    records = sf_client.tooling_query(SOQL)
    findings = []

    for r in records:
        if not r.get("Active"):
            continue
        if not r.get("Description"):
            obj = (r.get("EntityDefinition") or {}).get("QualifiedApiName", "Unknown")
            name = r.get("ValidationName", "Unknown")
            findings.append(Finding(
                category="Validation",
                severity="Info",
                title="Active validation rule has no description",
                detail=f"{obj}.{name} — no description",
                recommendation="Add a description explaining when this rule fires and why.",
            ))

    return findings
