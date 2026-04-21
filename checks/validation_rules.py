import re
from checks import Finding

_VALID_API_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# EntityDefinition.QualifiedApiName relationship traversal is not supported in
# Tooling API bulk SOQL. Query EntityDefinitionId and resolve names separately.
SOQL = (
    "SELECT Id, ValidationName, EntityDefinitionId, Description, Active "
    "FROM ValidationRule "
    "WHERE Active = true "
    "ORDER BY EntityDefinitionId"
)

ENTITY_SOQL = (
    "SELECT Id, QualifiedApiName "
    "FROM EntityDefinition "
    "WHERE IsCustomizable = true"
)


def check_validation_rules(sf_client) -> list[Finding]:
    records = sf_client.tooling_query(SOQL)
    if not records:
        return []

    # Build entity ID -> API name map
    entity_map: dict[str, str] = {}
    try:
        entities = sf_client.tooling_query(ENTITY_SOQL)
        entity_map = {e["Id"]: e["QualifiedApiName"] for e in entities if e.get("Id")}
    except Exception:
        pass

    findings = []
    for r in records:
        if not r.get("Active"):
            continue
        if not r.get("Description"):
            entity_id = r.get("EntityDefinitionId", "")
            obj = entity_map.get(entity_id, entity_id or "Unknown")
            name = r.get("ValidationName", "Unknown")
            rule_id = r.get("Id", "")
            obj_is_api_name = bool(obj) and obj != "Unknown" and bool(_VALID_API_NAME.match(obj))
            rule_link = (
                sf_client.sf_url(f"/lightning/setup/ObjectManager/{obj}/ValidationRules/{rule_id}/view")
                if rule_id and obj_is_api_name else ""
            )
            findings.append(Finding(
                category="Validation",
                severity="Info",
                title="Active validation rule has no description",
                detail=f"{obj}.{name} — no description",
                recommendation="Add a description explaining when this rule fires and why.",
                link=rule_link,
            ))

    return findings
