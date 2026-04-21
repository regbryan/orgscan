"""
Email Deliverability
Checks: org-wide email addresses, stale / unused email templates,
email relay TLS configuration, email service settings, and
DKIM domain verification (Salesforce Summer '26 enforcement).
"""
import re
from datetime import datetime, timedelta, timezone
from checks import Finding


# Matches a literal email address inside setSenderAddress('...') in Apex bodies
_APEX_SENDER_RE = re.compile(
    r'setSenderAddress\s*\(\s*[\'"]([^@\'"]+@([A-Za-z0-9._-]+\.[A-Za-z]{2,}))[\'"]',
    re.IGNORECASE,
)


_STALE_TEMPLATE_DAYS = 365


def check_email(sf_client) -> list[Finding]:
    findings = []

    # ── Org-Wide Email Addresses ──────────────────────────────────────────────
    try:
        owe = sf_client.query(
            "SELECT Id, Address, DisplayName, IsAllowAllProfiles FROM OrgWideEmailAddress"
        )
        if not owe:
            findings.append(Finding(
                category="Email",
                severity="Info",
                title="No org-wide email addresses configured",
                detail="Outbound emails use individual user addresses as the sender",
                recommendation=(
                    "Configure org-wide email addresses to control sender branding, "
                    "ensure replies reach shared inboxes, and improve deliverability."
                ),
                link=sf_client.sf_url("/lightning/setup/OrgWideEmailAddresses/home"),
            ))
        else:
            allow_all = [e for e in owe if e.get("IsAllowAllProfiles")]
            lines = "\n".join(
                f"{e.get('DisplayName', '?')} <{e.get('Address', '?')}> — "
                f"{'All profiles' if e.get('IsAllowAllProfiles') else 'Restricted profiles'}"
                for e in owe
            )
            findings.append(Finding(
                category="Email",
                severity="Info",
                title=f"{len(owe)} org-wide email address(es) configured",
                detail=lines,
                recommendation=(
                    "Verify these addresses are still active and monitored. "
                    "Addresses open to all profiles should be intentional."
                ),
                link=sf_client.sf_url("/lightning/setup/OrgWideEmailAddresses/home"),
            ))
    except Exception:
        pass

    # ── Email Templates ───────────────────────────────────────────────────────
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=_STALE_TEMPLATE_DAYS)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        templates = sf_client.query(
            "SELECT Id, Name, FolderName, LastUsedDate, TimesUsed, IsActive "
            "FROM EmailTemplate WHERE IsActive = true "
            "ORDER BY LastUsedDate ASC NULLS FIRST LIMIT 500"
        )
        if templates:
            stale = [
                t for t in templates
                if not t.get("LastUsedDate") or t.get("LastUsedDate", "") < cutoff
            ]
            never_used = [t for t in templates if not (t.get("TimesUsed") or 0)]

            if stale:
                lines = "\n".join(
                    f"{t.get('Name', '?')} ({t.get('FolderName', '?')}) — "
                    f"{'Never used' if not t.get('LastUsedDate') else 'Last: ' + t['LastUsedDate'][:10]}"
                    for t in stale[:15]
                )
                findings.append(Finding(
                    category="Email",
                    severity="Info",
                    title=f"{len(stale)} active email template(s) unused for 12+ months",
                    detail=lines,
                    recommendation=(
                        "Deactivate or archive email templates that are no longer in use. "
                        "A bloated template library makes it hard to find the right template."
                    ),
                    link=sf_client.sf_url("/lightning/setup/CommunicationTemplatesEmail/home"),
                ))

            if never_used:
                findings.append(Finding(
                    category="Email",
                    severity="Info",
                    title=f"{len(never_used)} active email template(s) never sent",
                    detail="\n".join(
                        f"{t.get('Name', '?')} ({t.get('FolderName', '?')})"
                        for t in never_used[:10]
                    ),
                    recommendation=(
                        "Templates that have never been sent may be duplicates, drafts, "
                        "or templates for retired processes. Review and remove to reduce clutter."
                    ),
                    link=sf_client.sf_url("/lightning/setup/CommunicationTemplatesEmail/home"),
                ))
    except Exception:
        pass

    # ── Email Relay Configuration ─────────────────────────────────────────────
    try:
        relays = sf_client.query("SELECT Id, Host, TlsSetting FROM EmailRelay LIMIT 10")
        if relays:
            weak_tls = [r for r in relays if r.get("TlsSetting") in ("", None, "NONE", "OPTIONAL")]
            if weak_tls:
                findings.append(Finding(
                    category="Email",
                    severity="Warning",
                    title=f"{len(weak_tls)} email relay host(s) with weak or no TLS",
                    detail="\n".join(
                        f"{r.get('Host', '?')} — TLS: {r.get('TlsSetting') or 'None'}"
                        for r in weak_tls
                    ),
                    recommendation=(
                        "Set TLS to 'REQUIRED' or 'REQUIRED_VERIFY_CA' on all email relay hosts "
                        "to ensure emails are encrypted in transit and not interceptable."
                    ),
                    link=sf_client.sf_url("/lightning/setup/EmailRelay/home"),
                ))
    except Exception:
        pass

    # ── Email Services ────────────────────────────────────────────────────────
    try:
        services = sf_client.query(
            "SELECT Id, DeveloperName, IsActive FROM EmailServicesFunction WHERE IsActive = true LIMIT 50"
        )
        if services:
            lines = "\n".join(s.get("DeveloperName", "?") for s in services[:10])
            findings.append(Finding(
                category="Email",
                severity="Info",
                title=f"{len(services)} active inbound Email Service(s)",
                detail=lines,
                recommendation=(
                    "Review active email services to ensure their Apex handlers are still "
                    "maintained and the receiving addresses are documented."
                ),
                link=sf_client.sf_url("/lightning/setup/EmailToApex/home"),
            ))
    except Exception:
        pass

    return findings


def check_email_domain_verification(sf_client) -> list[Finding]:
    """
    Salesforce Summer '26 enforcement: every domain used to send email from this org
    must have an active DKIM key, or outbound emails will be blocked/rejected.

    Sources scanned:
    - Org-Wide Email Addresses (OWEAs)
    - Workflow Email Alerts with a custom From address
    - Active Apex classes calling setSenderAddress() with a literal address

    Surfaces:
    - Sending domains with no active DKIM key (Critical)
    - DKIM keys created but not yet activated (Warning)
    - Apex classes using setSenderAddress() with a dynamic/variable From (Warning — needs manual review)
    - No DKIM configured at all (Warning)
    - All sending domains verified (Info)
    """
    findings = []

    # domain -> list of human-readable source labels
    domain_sources: dict[str, list[str]] = {}

    def _add(addr: str, label: str) -> None:
        addr = addr.strip()
        if "@" in addr:
            d = addr.split("@", 1)[1].lower()
            domain_sources.setdefault(d, []).append(label)

    # ── Source 1: Org-Wide Email Addresses ────────────────────────────────────
    try:
        for r in sf_client.query("SELECT Address FROM OrgWideEmailAddress"):
            _add(r.get("Address") or "", f"Org-Wide Address: {r.get('Address', '?')}")
    except Exception:
        pass

    # ── Source 2: Workflow Email Alert sender addresses ───────────────────────
    # WorkflowAlert.SenderType = 'OrgWideEmailAddress' means a custom From was chosen;
    # CurrentUser / DefaultWorkflowUser use the running user's address (not a fixed domain).
    try:
        alerts = sf_client.tooling_query(
            "SELECT Id, DeveloperName, SenderType, SenderAddress FROM WorkflowAlert "
            "WHERE SenderType = 'OrgWideEmailAddress'"
        )
        for a in alerts:
            name = a.get("DeveloperName", "Unknown")
            _add(a.get("SenderAddress") or "", f"Workflow Alert: {name}")
    except Exception:
        pass

    # ── Source 3: Apex classes with setSenderAddress() ───────────────────────
    # We scan for literal email addresses in the call. If setSenderAddress() is
    # called with a variable or custom label, we can't extract the domain — those
    # classes are surfaced separately for manual review.
    apex_dynamic: list[str] = []  # class names where address is not a literal
    try:
        classes = sf_client.query(
            "SELECT Id, Name, Body FROM ApexClass "
            "WHERE Status = 'Active' AND Body LIKE '%setSenderAddress%'"
        )
        for c in classes:
            name = c.get("Name", "Unknown")
            body = c.get("Body") or ""
            matches = _APEX_SENDER_RE.findall(body)  # returns (full_email, domain) tuples
            if matches:
                for full_addr, _ in matches:
                    _add(full_addr, f"Apex: {name}")
            else:
                # setSenderAddress is present but uses a variable — can't resolve statically
                apex_dynamic.append(name)
    except Exception:
        pass

    # ── Collect active and inactive DKIM keys ────────────────────────────────
    active_dkim: set[str] = set()
    inactive_dkim: set[str] = set()
    try:
        for k in sf_client.tooling_query("SELECT Id, DomainName, IsActive FROM DkimKey"):
            d = (k.get("DomainName") or "").lower().strip()
            if not d:
                continue
            if k.get("IsActive"):
                active_dkim.add(d)
            else:
                inactive_dkim.add(d)
    except Exception:
        pass

    # ── Cross-reference: sending domains vs active DKIM ──────────────────────
    if domain_sources:
        unverified = sorted(d for d in domain_sources if d not in active_dkim)
        verified = sorted(d for d in domain_sources if d in active_dkim)

        if unverified:
            lines = []
            for d in unverified:
                sources = "; ".join(domain_sources[d][:4])
                note = "(DKIM key inactive)" if d in inactive_dkim else "(no DKIM key)"
                lines.append(f"{d}  {note}\n  Used by: {sources}")
            findings.append(Finding(
                category="Email",
                severity="Critical",
                title=f"{len(unverified)} sending domain(s) at risk — DKIM not active",
                detail=(
                    "Salesforce Summer '26 requires domain verification for all outbound email "
                    "sending domains. Emails from unverified domains will be blocked or rejected.\n\n"
                    + "\n".join(lines)
                ),
                recommendation=(
                    "For each unverified domain:\n"
                    "1. Setup → DKIM Keys → New Key (select the domain)\n"
                    "2. Publish the CNAME record Salesforce provides to your DNS\n"
                    "3. Wait 24–48 hrs for propagation, then click Activate\n"
                    "Also confirm SPF includes Salesforce: include:_spf.salesforce.com"
                ),
                link=sf_client.sf_url("/lightning/setup/DkimKeys/home"),
            ))

        if verified:
            findings.append(Finding(
                category="Email",
                severity="Info",
                title=f"{len(verified)} sending domain(s) verified with active DKIM",
                detail="\n".join(
                    f"{d}  (used by: {'; '.join(domain_sources[d][:3])})"
                    for d in verified
                ),
                recommendation=(
                    "Confirm CNAME records remain published and keys have not expired. "
                    "Monitor deliverability reports for bounce rate increases."
                ),
                link=sf_client.sf_url("/lightning/setup/DkimKeys/home"),
            ))

    # ── Pending DKIM keys not yet linked to a known sending domain ───────────
    pending_only = inactive_dkim - set(domain_sources.keys())
    if pending_only:
        findings.append(Finding(
            category="Email",
            severity="Warning",
            title=f"{len(pending_only)} DKIM key(s) created but not yet activated",
            detail="\n".join(
                f"{d} — awaiting DNS propagation and activation"
                for d in sorted(pending_only)
            ),
            recommendation=(
                "Publish the CNAME record to your DNS provider, then return to "
                "Setup → DKIM Keys and click Activate after DNS propagates (24–48 hrs)."
            ),
            link=sf_client.sf_url("/lightning/setup/DkimKeys/home"),
        ))

    # ── Apex classes using setSenderAddress() with a dynamic/variable From ───
    if apex_dynamic:
        findings.append(Finding(
            category="Email",
            severity="Warning",
            title=f"{len(apex_dynamic)} Apex class(es) send email with a dynamic From address",
            detail=(
                "These classes call setSenderAddress() with a variable or custom label — "
                "the actual sending domain cannot be determined statically. "
                "Verify those domains have DKIM configured.\n\n"
                + "\n".join(apex_dynamic[:20])
            ),
            recommendation=(
                "Open each class and trace the value passed to setSenderAddress(). "
                "Ensure every domain it could resolve to has an active DKIM key in "
                "Setup → DKIM Keys."
            ),
            link=sf_client.sf_url("/lightning/setup/ApexClasses/home"),
        ))

    # ── No DKIM at all ────────────────────────────────────────────────────────
    if not domain_sources and not active_dkim and not inactive_dkim:
        findings.append(Finding(
            category="Email",
            severity="Warning",
            title="No DKIM keys configured — email deliverability at risk",
            detail=(
                "No DKIM keys are set up. Emails sent via Salesforce flows, workflow alerts, "
                "and Apex originate from Salesforce mail servers without domain authentication, "
                "making them more likely to fail spam filters or be blocked."
            ),
            recommendation=(
                "Set up DKIM for your primary sending domain: Setup → DKIM Keys → New Key. "
                "Also verify SPF includes Salesforce: include:_spf.salesforce.com"
            ),
            link=sf_client.sf_url("/lightning/setup/DkimKeys/home"),
        ))

    return findings
