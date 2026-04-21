"""
Duplicate detection for Salesforce records.

Two modes:
  1. native  — reads from Salesforce DuplicateRecordSet / DuplicateRecordItem objects.
               Works only when the org has Active duplicate rules configured.
  2. custom  — SOQL + server-side grouping by normalized field values.
               Works on any org, no special setup required.
"""

from __future__ import annotations
import re
import unicodedata

# ---------------------------------------------------------------------------
# Object catalogue — what we can scan and how
# ---------------------------------------------------------------------------

SUPPORTED_OBJECTS: dict[str, dict] = {
    "Account": {
        "label": "Accounts",
        "soql_fields": "Id, Name, Phone, Website, BillingStreet, BillingCity, BillingState, OwnerId, CreatedDate, LastModifiedDate",
        "match_fields": [
            {"value": "Name",         "label": "Account Name"},
            {"value": "Website",      "label": "Website"},
            {"value": "Phone",        "label": "Phone"},
            {"value": "BillingStreet","label": "Billing Street"},
        ],
        "merge_path": "accmerge",
    },
    "Contact": {
        "label": "Contacts",
        "soql_fields": "Id, Name, FirstName, LastName, Email, Phone, MobilePhone, AccountId, OwnerId, CreatedDate, LastModifiedDate",
        "match_fields": [
            {"value": "FirstName",   "label": "First Name"},
            {"value": "LastName",    "label": "Last Name"},
            {"value": "Email",       "label": "Email"},
            {"value": "Phone",       "label": "Phone"},
            {"value": "MobilePhone", "label": "Mobile Phone"},
        ],
        "merge_path": "conmerge",
    },
    "Lead": {
        "label": "Leads",
        "soql_fields": "Id, Name, FirstName, LastName, Email, Phone, Company, Status, OwnerId, CreatedDate, LastModifiedDate",
        "match_fields": [
            {"value": "FirstName", "label": "First Name"},
            {"value": "LastName",  "label": "Last Name"},
            {"value": "Email",     "label": "Email"},
            {"value": "Phone",     "label": "Phone"},
            {"value": "Company",   "label": "Company"},
        ],
        "merge_path": "leadmerge",
    },
}

MAX_RECORDS = 5_000  # max records pulled per scan


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize(val: str) -> str:
    """Lowercase, strip whitespace and common separators for field comparison."""
    if not val:
        return ""
    val = unicodedata.normalize("NFKC", str(val))
    val = val.lower().strip()
    val = re.sub(r"[\s\-\.\+\(\)\/\\]", "", val)
    return val


def _compound_key(record: dict, fields: list[str]) -> str:
    """Return a '|||'-joined normalised key across the selected fields."""
    return "|||".join(_normalize(str(record.get(f) or "")) for f in fields)


def _key_is_empty(key: str) -> bool:
    return all(part == "" for part in key.split("|||"))


# ---------------------------------------------------------------------------
# Custom matching (SOQL + Python grouping)
# ---------------------------------------------------------------------------

def scan_duplicates_custom(sf_client, object_name: str, match_fields: list[str]) -> tuple[list[dict], int]:
    """
    Pull records from Salesforce and group by normalized match_fields.
    Returns (groups, records_scanned) where groups is a list of duplicate groups
    and records_scanned is the total number of records fetched.
    """
    cfg = SUPPORTED_OBJECTS.get(object_name)
    if not cfg:
        return [], 0

    soql = (
        f"SELECT {cfg['soql_fields']} FROM {object_name} "
        f"WHERE IsDeleted = false "
        f"ORDER BY CreatedDate ASC LIMIT {MAX_RECORDS}"
    )
    try:
        records = sf_client.query(soql)
    except Exception as exc:
        raise RuntimeError(f"Failed to query {object_name}: {exc}") from exc

    records_scanned = len(records)

    # Group records by normalised key
    buckets: dict[str, list[dict]] = {}
    for rec in records:
        key = _compound_key(rec, match_fields)
        if _key_is_empty(key):
            continue
        buckets.setdefault(key, []).append(rec)

    groups = []
    for gid, (key, recs) in enumerate(buckets.items()):
        if len(recs) < 2:
            continue
        # Oldest record first (best merge master candidate)
        recs_sorted = sorted(recs, key=lambda r: r.get("CreatedDate") or "")
        groups.append({
            "group_id": gid,
            "object_name": object_name,
            "count": len(recs_sorted),
            "match_fields": match_fields,
            "match_key": key,
            "records": [_clean_record(r) for r in recs_sorted],
        })

    return sorted(groups, key=lambda g: g["count"], reverse=True), records_scanned


# ---------------------------------------------------------------------------
# Native matching (DuplicateRecordSet / DuplicateRecordItem)
# ---------------------------------------------------------------------------

def scan_duplicates_native(sf_client, object_name: str) -> list[dict]:
    """
    Read duplicate groups already detected by Salesforce's own duplicate rules.
    Returns the same group structure as scan_duplicates_custom.
    """
    try:
        sets = sf_client.query(
            f"SELECT Id, DuplicateRuleId, RecordCount FROM DuplicateRecordSet "
            f"WHERE DuplicateRule.SobjectType = '{object_name}' AND RecordCount >= 2 "
            f"ORDER BY RecordCount DESC LIMIT 500"
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not query DuplicateRecordSet — ensure the org has active "
            f"duplicate rules for {object_name}. Detail: {exc}"
        ) from exc

    if not sets:
        return []

    cfg = SUPPORTED_OBJECTS.get(object_name)
    soql_fields = cfg["soql_fields"] if cfg else "Id, Name, CreatedDate, LastModifiedDate"

    groups = []
    for gid, ds in enumerate(sets):
        set_id = ds["Id"]
        try:
            items = sf_client.query(
                f"SELECT RecordId FROM DuplicateRecordItem WHERE DuplicateRecordSetId = '{set_id}'"
            )
        except Exception:
            continue

        record_ids = [i["RecordId"] for i in items if i.get("RecordId")]
        if len(record_ids) < 2:
            continue

        id_list = "','".join(record_ids)
        try:
            records = sf_client.query(
                f"SELECT {soql_fields} FROM {object_name} "
                f"WHERE Id IN ('{id_list}') AND IsDeleted = false"
            )
        except Exception:
            # Fall back to stubs so the group still appears
            records = [{"Id": rid, "Name": f"Record {rid[:6]}…"} for rid in record_ids]

        if len(records) < 2:
            continue

        recs_sorted = sorted(records, key=lambda r: r.get("CreatedDate") or "")
        groups.append({
            "group_id": gid,
            "object_name": object_name,
            "count": len(recs_sorted),
            "match_fields": ["Salesforce duplicate rule"],
            "match_key": set_id,
            "records": [_clean_record(r) for r in recs_sorted],
        })

    return groups


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_record(rec: dict) -> dict:
    """Strip Salesforce metadata cruft (attributes) from a record dict."""
    return {k: v for k, v in rec.items() if k != "attributes"}


# ---------------------------------------------------------------------------
# Cross-object scan: Leads that already have a matching Contact
# ---------------------------------------------------------------------------

# Fields to pull for cross-object matching
_LEAD_FIELDS    = "Id, FirstName, LastName, Name, Email, Phone, Company, Status, OwnerId, CreatedDate, LastModifiedDate"
_CONTACT_FIELDS = "Id, FirstName, LastName, Name, Email, Phone, AccountId, OwnerId, CreatedDate, LastModifiedDate"

# Fields the user can choose to match on (same field name exists on both objects).
# Matching uses a compound key — ALL selected fields must match (AND logic),
# consistent with how Salesforce's own duplicate rules work for name fields.
CROSS_MATCH_FIELDS: list[dict] = [
    {"value": "Email",     "label": "Email"},
    {"value": "Phone",     "label": "Phone"},
    {"value": "FirstName", "label": "First Name"},
    {"value": "LastName",  "label": "Last Name"},
]


def scan_cross_object_leads_contacts(
    sf_client,
    match_fields: list[str],
) -> tuple[list[dict], int, int]:
    """
    Find unconverted Leads that have a matching Contact on ALL of match_fields.

    Uses compound-key AND matching: a Lead matches a Contact only when every
    selected field normalises to the same value on both records.  This mirrors
    how Salesforce duplicate rules evaluate name / email / phone fields.

    Returns (matches, leads_scanned, contacts_scanned) where matches is a list of:
      - lead:       the Lead record
      - contacts:   list of matching Contact records
      - matched_on: the fields used for matching
    """
    if not match_fields:
        raise ValueError("At least one match field is required.")

    # Pull unconverted leads
    try:
        leads = sf_client.query(
            f"SELECT {_LEAD_FIELDS} FROM Lead "
            f"WHERE IsConverted = false AND IsDeleted = false "
            f"ORDER BY CreatedDate ASC LIMIT {MAX_RECORDS}"
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to query Leads: {exc}") from exc

    leads_scanned = len(leads)
    if not leads:
        return [], 0, 0

    # Pull contacts
    try:
        contacts = sf_client.query(
            f"SELECT {_CONTACT_FIELDS} FROM Contact "
            f"WHERE IsDeleted = false "
            f"ORDER BY CreatedDate ASC LIMIT {MAX_RECORDS}"
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to query Contacts: {exc}") from exc

    contacts_scanned = len(contacts)
    if not contacts:
        return [], leads_scanned, 0

    # Build compound-key index on contacts (ALL selected fields must match)
    contact_index: dict[str, list[dict]] = {}
    for c in contacts:
        c = _clean_record(c)
        key = _compound_key(c, match_fields)
        if _key_is_empty(key):
            continue
        contact_index.setdefault(key, []).append(c)

    # Match each lead against the contact index
    groups: list[dict] = []
    for gid, lead in enumerate(leads):
        lead = _clean_record(lead)
        key = _compound_key(lead, match_fields)
        if _key_is_empty(key):
            continue
        matching_contacts = contact_index.get(key, [])
        if not matching_contacts:
            continue
        groups.append({
            "group_id": gid,
            "lead": lead,
            "contacts": matching_contacts,
            "matched_on": match_fields,
        })

    # Most contact matches first
    return sorted(groups, key=lambda g: len(g["contacts"]), reverse=True), leads_scanned, contacts_scanned


def convert_lead_url(instance_url: str, lead_id: str) -> str:
    """Return the Salesforce Lead Convert URL (works in Lightning via redirect)."""
    return f"{instance_url}/_ui/sales/lead/ConvertLeadPage?id={lead_id}"


def merge_url(instance_url: str, object_name: str, record_ids: list[str]) -> str:
    """
    Build the Salesforce classic merge URL for up to 3 records.
    These URLs work in Lightning Experience as well.
    """
    cfg = SUPPORTED_OBJECTS.get(object_name, {})
    merge_path = cfg.get("merge_path", "")
    if not merge_path or not record_ids:
        return ""
    base = instance_url.rstrip("/")
    ids_qs = "&".join(f"ids{i}={rid}" for i, rid in enumerate(record_ids[:3]))
    return f"{base}/merge/{merge_path}.jsp?{ids_qs}"
