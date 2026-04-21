import re
from checks import Finding

# A valid Salesforce API name starts with a letter and contains only word chars
_VALID_API_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# CustomField is a reliable Tooling API object that lists all custom fields
# without requiring a per-entity filter (unlike FieldDefinition).
# ManageableState = 'unmanaged' = org-native fields (not from packages).
FIELD_SOQL = (
    "SELECT Id, DeveloperName, EntityDefinitionId, TableEnumOrId, "
    "NamespacePrefix, Description "
    "FROM CustomField "
    "WHERE ManageableState = 'unmanaged' "
    "ORDER BY EntityDefinitionId"
)

# Fetch all metadata that references custom fields (flows, reports, page layouts, etc.)
DEPENDENCY_SOQL = (
    "SELECT MetadataComponentName, MetadataComponentType, RefMetadataComponentName "
    "FROM MetadataComponentDependency "
    "WHERE RefMetadataComponentType = 'CustomField'"
)

_AUTOMATION_TYPES = {"Flow", "WorkflowRule", "ProcessBuilder", "ApexClass", "ApexTrigger"}
_REPORT_TYPES = {"Report", "ReportType"}
_LAYOUT_TYPES = {"Layout", "FlexiPage", "CompactLayout"}


def _build_entity_map(sf_client, entity_ids: set[str]) -> dict[str, str]:
    """
    Build {entity_id: QualifiedApiName} for resolving field → object names.

    Custom field TableEnumOrId values can be:
      - API name directly  ("Account", "Contact__c") for standard objects
      - 15/18-char ID starting with 01I for custom objects (CustomObject records)

    We query both EntityDefinition (standard objects, returns 01I IDs too) and
    CustomObject Tooling API (reliable for custom objects) and index by both
    15- and 18-char ID forms.
    """
    entity_map: dict[str, str] = {}

    def _store(eid: str, name: str) -> None:
        if eid and name:
            entity_map[eid] = name
            entity_map[eid[:15]] = name

    # EntityDefinition covers standard + custom objects that are "customizable"
    try:
        for row in sf_client.tooling_query(
            "SELECT Id, QualifiedApiName FROM EntityDefinition WHERE IsCustomizable = true"
        ):
            _store(row.get("Id", ""), row.get("QualifiedApiName", ""))
    except Exception:
        pass

    # CustomObject Tooling API covers custom objects by their 01I... IDs directly
    try:
        for row in sf_client.tooling_query(
            "SELECT Id, DeveloperName, NamespacePrefix FROM CustomObject"
        ):
            eid  = row.get("Id", "")
            dev  = row.get("DeveloperName", "")
            ns   = row.get("NamespacePrefix") or ""
            name = f"{ns}__{dev}__c" if ns else f"{dev}__c"
            _store(eid, name)
    except Exception:
        pass

    return entity_map


def _build_dependency_map(sf_client) -> dict[str, list[str]]:
    """Returns {field_ref_name_lower: [list of 'ComponentType: Name' strings]}."""
    dep_map: dict[str, list[str]] = {}
    try:
        deps = sf_client.tooling_query(DEPENDENCY_SOQL)
        for d in deps:
            ref = (d.get("RefMetadataComponentName") or "").lower()
            comp_type = d.get("MetadataComponentType") or "Unknown"
            comp_name = d.get("MetadataComponentName") or "Unknown"
            dep_map.setdefault(ref, []).append(f"{comp_type}: {comp_name}")
    except Exception:
        pass
    return dep_map


def check_unused_fields(sf_client) -> list[Finding]:
    records = sf_client.tooling_query(FIELD_SOQL)
    if not records:
        return []

    # Collect all unique entity IDs from the field records, then resolve in one batch
    entity_ids = {
        r.get("EntityDefinitionId") or r.get("TableEnumOrId") or ""
        for r in records
    } - {""}
    entity_map = _build_entity_map(sf_client, entity_ids)
    dep_map    = _build_dependency_map(sf_client)
    findings   = []

    for r in records:
        dev_name = r.get("DeveloperName", "Unknown")
        ns = r.get("NamespacePrefix") or ""
        # Build the full API name: Namespace__FieldName__c or FieldName__c
        field_api = (f"{ns}__{dev_name}__c" if ns else f"{dev_name}__c")

        # Resolve object name from EntityDefinitionId or TableEnumOrId
        raw_entity = r.get("EntityDefinitionId") or r.get("TableEnumOrId") or ""
        obj = entity_map.get(raw_entity, raw_entity or "Unknown")

        # Look up dependencies — try "Object.Field__c" and "Field__c" forms
        refs = (
            dep_map.get(f"{obj}.{field_api}".lower()) or
            dep_map.get(field_api.lower()) or
            []
        )

        automations = [c for c in refs if c.split(":")[0].strip() in _AUTOMATION_TYPES]
        reports     = [c for c in refs if c.split(":")[0].strip() in _REPORT_TYPES]
        layouts     = [c for c in refs if c.split(":")[0].strip() in _LAYOUT_TYPES]
        other       = [c for c in refs if c not in automations and c not in reports and c not in layouts]

        field_id = r.get("Id", "")
        # TableEnumOrId is directly the object API name (e.g. "Account") — use it
        # for the link instead of going through the entity map, which may fail or
        # return a raw entity ID when EntityDefinitionId is present.
        table_name = r.get("TableEnumOrId") or ""
        link_obj = table_name if _VALID_API_NAME.match(table_name) else (
            obj if _VALID_API_NAME.match(obj or "") else ""
        )
        field_link = (
            sf_client.sf_url(f"/lightning/setup/ObjectManager/{link_obj}/FieldsAndRelationships/{field_id}/view")
            if field_id and link_obj else ""
        )

        if refs:
            usage_lines = []
            if automations:
                usage_lines.append("Automations: " + ", ".join(a.split(": ", 1)[-1] for a in automations))
            if reports:
                usage_lines.append("Reports: " + ", ".join(x.split(": ", 1)[-1] for x in reports))
            if layouts:
                usage_lines.append("Layouts: " + ", ".join(x.split(": ", 1)[-1] for x in layouts))
            if other:
                usage_lines.append("Other: " + ", ".join(o.split(": ", 1)[-1] for o in other))
            detail = f"{obj}.{field_api} — referenced but no data\n" + "\n".join(usage_lines)
            findings.append(Finding(
                category="Fields",
                severity="Info",
                title=f"{obj}.{field_api} — empty field still referenced",
                detail=detail,
                recommendation=(
                    "Field has no data but is referenced by a flow, report, or layout. "
                    "Verify it is intentional before deleting."
                ),
                link=field_link,
            ))
        else:
            findings.append(Finding(
                category="Fields",
                severity="Warning",
                title=f"{obj}.{field_api} — no references found",
                detail="Not referenced in any flow, report, or layout",
                recommendation=(
                    "Safe to delete if the business no longer needs it. "
                    "Always confirm with stakeholders before removing."
                ),
                link=field_link,
            ))

    return findings
