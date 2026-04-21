"""
Data Quality Assessment
Checks: incomplete records (missing key fields), stale leads,
record counts by object, and accounts with no contacts.
Duplicate detection is handled separately by checks/duplicates.py.
"""
from datetime import datetime, timedelta, timezone
from checks import Finding


_STALE_LEAD_DAYS = 365


def _count(sf_client, soql: str) -> int:
    """Run a SELECT COUNT(Id) aggregate query and return the integer count."""
    try:
        result = sf_client.query(soql)
        if result and isinstance(result[0], dict):
            for key in ("expr0", "cnt", "total"):
                if key in result[0]:
                    return int(result[0][key] or 0)
    except Exception:
        pass
    return 0


def check_data_quality(sf_client) -> list[Finding]:
    findings = []
    stale_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=_STALE_LEAD_DAYS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Record count summary ──────────────────────────────────────────────────
    counts: dict[str, int] = {}
    for obj, soql in [
        ("Account",     "SELECT COUNT(Id) FROM Account"),
        ("Contact",     "SELECT COUNT(Id) FROM Contact"),
        ("Lead",        "SELECT COUNT(Id) FROM Lead WHERE IsConverted = false"),
        ("Opportunity", "SELECT COUNT(Id) FROM Opportunity"),
        ("Case",        "SELECT COUNT(Id) FROM Case"),
    ]:
        n = _count(sf_client, soql)
        if n > 0:
            counts[obj] = n

    if counts:
        findings.append(Finding(
            category="Data Quality",
            severity="Info",
            title="Record count summary",
            detail="\n".join(f"{obj}: {n:,}" for obj, n in counts.items()),
            recommendation=(
                "Use record counts to spot unexpected data volumes. "
                "High lead counts with low conversion rates indicate stale pipeline data."
            ),
        ))

    # ── Contacts missing Email ────────────────────────────────────────────────
    no_email_c = _count(sf_client, "SELECT COUNT(Id) FROM Contact WHERE Email = null")
    total_c    = counts.get("Contact") or _count(sf_client, "SELECT COUNT(Id) FROM Contact")
    if no_email_c > 0 and total_c > 0:
        pct = (no_email_c / total_c) * 100
        findings.append(Finding(
            category="Data Quality",
            severity="Warning" if pct >= 20 else "Info",
            title=f"{no_email_c:,} Contact(s) missing Email ({pct:.0f}%)",
            detail=f"{no_email_c:,} of {total_c:,} Contacts have no email address",
            recommendation=(
                "Contacts without email cannot receive campaigns or automated emails. "
                "Add a validation rule to require email on new contacts, "
                "and run a data enrichment campaign for existing records."
            ),
            link=sf_client.sf_url("/lightning/o/Contact/list?filterName=AllContacts"),
        ))

    # ── Contacts missing all phone numbers ───────────────────────────────────
    no_phone_c = _count(sf_client,
        "SELECT COUNT(Id) FROM Contact WHERE Phone = null AND MobilePhone = null")
    if no_phone_c > 0 and total_c > 0:
        pct = (no_phone_c / total_c) * 100
        if pct >= 30:
            findings.append(Finding(
                category="Data Quality",
                severity="Info",
                title=f"{no_phone_c:,} Contact(s) missing all phone numbers ({pct:.0f}%)",
                detail=f"{no_phone_c:,} Contacts have no Phone or Mobile Phone",
                recommendation=(
                    "Consider requiring at least one phone number. "
                    "Data enrichment tools (Clearbit, ZoomInfo) can backfill missing contact info."
                ),
                link=sf_client.sf_url("/lightning/o/Contact/list?filterName=AllContacts"),
            ))

    # ── Leads missing Email ───────────────────────────────────────────────────
    lead_count = counts.get("Lead", 0)
    no_email_l = _count(sf_client,
        "SELECT COUNT(Id) FROM Lead WHERE Email = null AND IsConverted = false")
    if no_email_l > 0 and lead_count > 0:
        pct = (no_email_l / lead_count) * 100
        findings.append(Finding(
            category="Data Quality",
            severity="Warning" if pct >= 20 else "Info",
            title=f"{no_email_l:,} Lead(s) missing Email ({pct:.0f}%)",
            detail=f"{no_email_l:,} of {lead_count:,} open Leads have no email address",
            recommendation=(
                "Leads without email cannot enter nurture sequences. "
                "Review lead capture forms and consider requiring email."
            ),
            link=sf_client.sf_url("/lightning/o/Lead/list?filterName=AllOpenLeads"),
        ))

    # ── Leads missing Company ─────────────────────────────────────────────────
    no_company_l = _count(sf_client,
        "SELECT COUNT(Id) FROM Lead WHERE Company = null AND IsConverted = false")
    if no_company_l > 0 and lead_count > 0:
        pct = (no_company_l / lead_count) * 100
        if pct >= 10:
            findings.append(Finding(
                category="Data Quality",
                severity="Info",
                title=f"{no_company_l:,} Lead(s) missing Company ({pct:.0f}%)",
                detail=f"{no_company_l:,} open Leads have no Company value",
                recommendation=(
                    "Company is required to convert a Lead to an Account. "
                    "Update lead capture forms and add a validation rule."
                ),
                link=sf_client.sf_url("/lightning/o/Lead/list?filterName=AllOpenLeads"),
            ))

    # ── Stale Leads (not modified in 12+ months) ──────────────────────────────
    stale_leads = _count(sf_client,
        f"SELECT COUNT(Id) FROM Lead "
        f"WHERE IsConverted = false AND LastModifiedDate < {stale_cutoff}")
    if stale_leads > 0:
        pct = (stale_leads / lead_count * 100) if lead_count else 0
        findings.append(Finding(
            category="Data Quality",
            severity="Warning" if stale_leads > 500 else "Info",
            title=f"{stale_leads:,} Lead(s) untouched for 12+ months ({pct:.0f}% of open leads)",
            detail=(
                f"{stale_leads:,} open Leads have had no activity in over a year. "
                "These inflate the pipeline and may be prospects who have moved on."
            ),
            recommendation=(
                "Run a lead re-engagement campaign or disqualify/archive these records. "
                "Set up assignment rules and SLA alerts to prevent leads from going cold."
            ),
            link=sf_client.sf_url("/lightning/o/Lead/list?filterName=AllOpenLeads"),
        ))

    # ── Accounts with no Contacts ─────────────────────────────────────────────
    acct_count = counts.get("Account", 0)
    if acct_count > 0:
        no_contact_accts = _count(sf_client,
            "SELECT COUNT(Id) FROM Account "
            "WHERE Id NOT IN (SELECT AccountId FROM Contact WHERE AccountId != null)")
        if no_contact_accts > 0:
            pct = (no_contact_accts / acct_count) * 100
            if pct >= 20:
                findings.append(Finding(
                    category="Data Quality",
                    severity="Info",
                    title=f"{no_contact_accts:,} Account(s) with no associated Contacts ({pct:.0f}%)",
                    detail=f"{no_contact_accts:,} of {acct_count:,} Accounts have zero contacts",
                    recommendation=(
                        "Accounts without contacts are dead ends for outreach. "
                        "Set up enrichment processes or assignment rules to ensure every "
                        "active account has at least one contact."
                    ),
                    link=sf_client.sf_url("/lightning/o/Account/list?filterName=AllAccounts"),
                ))

    return findings
