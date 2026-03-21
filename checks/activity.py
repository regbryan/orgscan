from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from checks import Finding


@dataclass
class ActivityEvent:
    event_type: str       # "Login" or "Setup Change"
    user: str             # username or display name
    action: str           # what happened
    timestamp: str        # ISO string
    ip_address: str       # IP or empty string
    status: str           # "Success", "Failed", "Warning"


def get_activity_log(sf_client, days: int = 30) -> list[ActivityEvent]:
    """Pull LoginHistory + SetupAuditTrail for the past `days` days."""
    events = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # LoginHistory
    login_soql = (
        f"SELECT UserId, Username, LoginTime, SourceIp, Status, LoginType "
        f"FROM LoginHistory "
        f"WHERE LoginTime >= {cutoff} "
        f"ORDER BY LoginTime DESC LIMIT 200"
    )
    try:
        logins = sf_client.query(login_soql)
        for r in logins:
            status = "Success" if r.get("Status") == "Success" else "Failed"
            events.append(ActivityEvent(
                event_type="Login",
                user=r.get("Username", "Unknown"),
                action=f"{r.get('LoginType', 'Unknown')} login",
                timestamp=r.get("LoginTime", ""),
                ip_address=r.get("SourceIp") or "",
                status=status,
            ))
    except Exception:
        pass  # LoginHistory may not be accessible in all editions

    # SetupAuditTrail
    audit_soql = (
        f"SELECT CreatedByContext, CreatedDate, Action, Section, Display, CreatedBy.Username "
        f"FROM SetupAuditTrail "
        f"WHERE CreatedDate >= {cutoff} "
        f"ORDER BY CreatedDate DESC LIMIT 200"
    )
    try:
        audits = sf_client.query(audit_soql)
        for r in audits:
            username = ""
            created_by = r.get("CreatedBy")
            if isinstance(created_by, dict):
                username = created_by.get("Username", "")
            events.append(ActivityEvent(
                event_type="Setup Change",
                user=username,
                action=r.get("Display") or r.get("Action") or "",
                timestamp=r.get("CreatedDate", ""),
                ip_address="",
                status="Warning",
            ))
    except Exception:
        pass

    # Sort all events newest first
    def sort_key(e):
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00").replace("+0000", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    events.sort(key=sort_key, reverse=True)
    return events


def get_activity_findings(sf_client) -> list[Finding]:
    """Health check findings derived from activity log."""
    findings = []
    events = get_activity_log(sf_client, days=30)

    login_events = [e for e in events if e.event_type == "Login"]
    failed_logins = [e for e in login_events if e.status == "Failed"]

    # Flag users with 5+ failed logins
    from collections import Counter
    fail_counts = Counter(e.user for e in failed_logins)
    repeat_failures = {u: c for u, c in fail_counts.items() if c >= 5}
    if repeat_failures:
        names = ", ".join(f"{u} ({c} failures)" for u, c in repeat_failures.items())
        findings.append(Finding(
            category="Activity",
            severity="Critical",
            title=f"{len(repeat_failures)} user(s) with 5+ failed login attempts",
            detail=names,
            recommendation="Investigate these accounts for potential brute-force attempts or compromised credentials.",
        ))

    # Flag admin setup changes
    setup_events = [e for e in events if e.event_type == "Setup Change"]
    if len(setup_events) > 20:
        findings.append(Finding(
            category="Activity",
            severity="Warning",
            title=f"{len(setup_events)} admin configuration changes in last 30 days",
            detail="High volume of org configuration changes detected.",
            recommendation="Review SetupAuditTrail to ensure all changes were authorized.",
        ))

    return findings
