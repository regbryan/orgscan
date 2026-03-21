from checks import Finding

SOQL = (
    "SELECT DeveloperName, EntityDefinition.QualifiedApiName, PopulatedCount, TotalCount "
    "FROM FieldDefinition "
    "WHERE EntityDefinition.IsCustomSetting = false "
    "AND IsCustom = true "
    "AND IsDeleted = false"
)


def check_unused_fields(sf_client) -> list[Finding]:
    records = sf_client.tooling_query(SOQL)
    findings = []

    for r in records:
        total = r.get("TotalCount") or 0
        populated = r.get("PopulatedCount") or 0
        if total == 0:
            continue
        if populated == 0:
            obj = (r.get("EntityDefinition") or {}).get("QualifiedApiName", "Unknown")
            name = r.get("DeveloperName", "Unknown")
            findings.append(Finding(
                category="Fields",
                severity="Warning",
                title="Unused custom field (zero population)",
                detail=f"{obj}.{name} — 0 of {total} records populated",
                recommendation="Consider deleting this field if it is no longer needed.",
            ))

    return findings
