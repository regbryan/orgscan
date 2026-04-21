import re
from checks import Finding

# EntityDefinition.QualifiedApiName relationship doesn't work in Tooling bulk SOQL.
# Fetch EntityDefinitionId and resolve separately.
LAYOUT_SOQL = (
    "SELECT Id, Name, EntityDefinitionId "
    "FROM Layout "
    "ORDER BY EntityDefinitionId"
)

PROFILE_LAYOUT_SOQL = "SELECT LayoutId FROM ProfileLayout"

# Custom Lightning pages (no managed namespace).
FLEXI_SOQL = (
    "SELECT Id, MasterLabel, DeveloperName, Type, EntityDefinitionId "
    "FROM FlexiPage "
    "WHERE NamespacePrefix = null"
)

_VALID_API_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


def _resolve_entity_names(sf_client, entity_ids: set[str]) -> dict[str, str]:
    """Fetch EntityDefinition records for the given IDs. Returns {id: QualifiedApiName}.

    Tries Tooling API first, then falls back to REST API query for any
    IDs that weren't resolved (some entity types aren't queryable via Tooling).
    """
    entity_map: dict[str, str] = {}
    if not entity_ids:
        return entity_map

    ids = list(entity_ids)

    # Attempt 1: Tooling API (works for most standard/custom objects)
    try:
        for i in range(0, len(ids), 200):
            chunk = ids[i : i + 200]
            id_list = "','".join(chunk)
            soql = f"SELECT Id, QualifiedApiName FROM EntityDefinition WHERE Id IN ('{id_list}')"
            rows = sf_client.tooling_query(soql)
            for e in rows:
                if e.get("Id") and e.get("QualifiedApiName"):
                    entity_map[e["Id"]] = e["QualifiedApiName"]
    except Exception:
        pass

    # Attempt 2: REST API for any still-missing IDs
    missing = [eid for eid in ids if eid not in entity_map]
    if missing:
        try:
            for i in range(0, len(missing), 200):
                chunk = missing[i : i + 200]
                id_list = "','".join(chunk)
                soql = f"SELECT Id, QualifiedApiName FROM EntityDefinition WHERE Id IN ('{id_list}')"
                rows = sf_client.query(soql)
                for e in rows:
                    if e.get("Id") and e.get("QualifiedApiName"):
                        entity_map[e["Id"]] = e["QualifiedApiName"]
        except Exception:
            pass

    return entity_map


def _valid_api(name: str) -> bool:
    return bool(name) and name != "Unknown" and bool(_VALID_API_NAME.match(name))


def _guess_object_from_layout_name(layout_name: str) -> str:
    """Try to extract the object name from a layout name.

    Salesforce page layout internal names often follow the pattern
    'ObjectName-Layout Name'.  If we can't resolve the EntityDefinition,
    this is a reasonable fallback.
    """
    if not layout_name:
        return ""
    # Pattern: "Account-Account Layout" → "Account"
    if "-" in layout_name:
        candidate = layout_name.split("-", 1)[0].strip()
        if _VALID_API_NAME.match(candidate):
            return candidate
    return ""


def check_unassigned_layouts(sf_client) -> list[Finding]:
    findings = []

    # ── Page layouts ──────────────────────────────────────────────────────────
    try:
        all_layouts  = sf_client.tooling_query(LAYOUT_SOQL)
        assigned_raw = sf_client.tooling_query(PROFILE_LAYOUT_SOQL)
        assigned_ids = {r["LayoutId"] for r in assigned_raw if r.get("LayoutId")}

        unassigned = [l for l in all_layouts if l.get("Id") not in assigned_ids]

        if unassigned:
            entity_ids = {l["EntityDefinitionId"] for l in unassigned if l.get("EntityDefinitionId")}
            entity_map = _resolve_entity_names(sf_client, entity_ids)

            for layout in unassigned:
                layout_id = layout.get("Id", "")
                entity_id = layout.get("EntityDefinitionId", "")
                name = layout.get("Name", "Unknown")
                obj = entity_map.get(entity_id, "") or _guess_object_from_layout_name(name) or "Unknown"

                # Direct link to this layout in Object Manager
                if layout_id and _valid_api(obj):
                    link = sf_client.sf_url(
                        f"/lightning/setup/ObjectManager/{obj}/PageLayouts/{layout_id}/view"
                    )
                else:
                    link = sf_client.sf_url("/lightning/setup/ObjectManager/home")

                findings.append(Finding(
                    category="Layouts",
                    severity="Warning",
                    title=f"{obj} — {name}",
                    detail="This page layout is not assigned to any profile or record type.",
                    recommendation=(
                        "Assign this layout to a profile via Object Manager → Page Layouts → "
                        "Page Layout Assignment, or delete it if it is no longer needed."
                    ),
                    link=link,
                ))
    except Exception:
        pass

    # ── Lightning pages (FlexiPage) ───────────────────────────────────────────
    try:
        all_pages = sf_client.tooling_query(FLEXI_SOQL)
        if all_pages:
            flexi_entity_ids = {
                p["EntityDefinitionId"]
                for p in all_pages
                if p.get("EntityDefinitionId")
            }
            flexi_entity_map = _resolve_entity_names(sf_client, flexi_entity_ids)

            for page in all_pages:
                page_id   = page.get("Id", "")
                label     = page.get("MasterLabel") or page.get("DeveloperName") or "Unknown"
                ptype     = page.get("Type") or "Unknown"
                entity_id = page.get("EntityDefinitionId") or ""
                obj       = flexi_entity_map.get(entity_id, "") if entity_id else ""

                title_prefix = f"{obj} — " if obj else ""
                title = f"{title_prefix}{label} ({ptype})"

                # Link opens the Lightning App Builder for this page
                link = (
                    sf_client.sf_url(f"/visualEditor/appHome.app?pageId={page_id}")
                    if page_id else sf_client.sf_url("/lightning/setup/FlexiPageList/home")
                )

                findings.append(Finding(
                    category="Layouts",
                    severity="Info",
                    title=title,
                    detail="Custom Lightning page — verify it is activated in App Builder.",
                    recommendation=(
                        "Open App Builder, confirm this page is activated for the correct "
                        "app/profile/record type, or delete it if no longer used."
                    ),
                    link=link,
                ))
    except Exception:
        pass

    return findings
