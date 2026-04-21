"""
Data Export & Import Activity
------------------------------
Surfaces who exported data and who pushed/imported data, using:
  1. SetupAuditTrail  — data export scheduling / downloads
  2. AsyncApexJob     — batch Apex / bulk processing jobs
  3. EventLogFile     — Salesforce Shield (gracefully skipped if not licensed)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from checks import Finding


@dataclass
class DataEvent:
    event_type: str    # "Export" | "Import" | "Batch Job" | "Shield"
    user: str
    action: str
    timestamp: str
    detail: str        # extra context (job status, record count, etc.)


def _cutoff(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── SetupAuditTrail export-related sections/actions ──────────────────────────
_EXPORT_SECTIONS = {"data export", "data management"}
_EXPORT_KEYWORDS = ("export", "import", "dataload", "data load", "backup")


def _is_export_action(section: str, action: str, display: str) -> bool:
    combined = f"{section} {action} {display}".lower()
    return any(kw in combined for kw in _EXPORT_KEYWORDS)


def get_data_events(sf_client, days: int = 90) -> list[DataEvent]:
    events: list[DataEvent] = []
    cut = _cutoff(days)

    # ── 1. SetupAuditTrail ───────────────────────────────────────────────────
    audit_soql = (
        f"SELECT CreatedDate, CreatedBy.Name, CreatedBy.Username, "
        f"Action, Section, Display "
        f"FROM SetupAuditTrail "
        f"WHERE CreatedDate >= {cut} "
        f"ORDER BY CreatedDate DESC LIMIT 500"
    )
    try:
        rows = sf_client.query(audit_soql)
        for r in rows:
            section = (r.get("Section") or "").lower()
            action  = (r.get("Action") or "").lower()
            display = r.get("Display") or ""

            if not _is_export_action(section, action, display):
                continue

            cb = r.get("CreatedBy") or {}
            name = cb.get("Name") or cb.get("Username") or "Unknown" if isinstance(cb, dict) else "Unknown"
            events.append(DataEvent(
                event_type="Export/Import",
                user=name,
                action=display or action,
                timestamp=r.get("CreatedDate", ""),
                detail=f"Section: {r.get('Section', '')}",
            ))
    except Exception:
        pass

    # ── 2. AsyncApexJob (Batch / Bulk data jobs) ─────────────────────────────
    job_soql = (
        f"SELECT Id, CreatedDate, CreatedBy.Name, CreatedBy.Username, "
        f"JobType, ApexClass.Name, Status, TotalJobItems, NumberOfErrors "
        f"FROM AsyncApexJob "
        f"WHERE CreatedDate >= {cut} "
        f"AND JobType IN ('BatchApex', 'BatchApexWorker', 'ScheduledApex') "
        f"ORDER BY CreatedDate DESC LIMIT 200"
    )
    try:
        jobs = sf_client.query(job_soql)
        for j in jobs:
            cb = j.get("CreatedBy") or {}
            name = cb.get("Name") or cb.get("Username") or "Unknown" if isinstance(cb, dict) else "Unknown"
            apex = (j.get("ApexClass") or {})
            class_name = apex.get("Name") or "Unknown" if isinstance(apex, dict) else "Unknown"
            total  = j.get("TotalJobItems") or 0
            errors = j.get("NumberOfErrors") or 0
            status = j.get("Status") or "Unknown"
            events.append(DataEvent(
                event_type="Batch Job",
                user=name,
                action=f"{j.get('JobType', '')} — {class_name}",
                timestamp=j.get("CreatedDate", ""),
                detail=f"Status: {status} | Batches: {total} | Errors: {errors}",
            ))
    except Exception:
        pass

    # ── 3. Salesforce Shield — EventLogFile ──────────────────────────────────
    shield_soql = (
        f"SELECT Id, EventType, LogDate, LogFileLength "
        f"FROM EventLogFile "
        f"WHERE EventType IN ('DataExport', 'ReportExport', 'BulkApi', 'BulkApiRequest') "
        f"AND LogDate >= {cut} "
        f"ORDER BY LogDate DESC LIMIT 100"
    )
    try:
        logs = sf_client.query(shield_soql)
        for lg in logs:
            events.append(DataEvent(
                event_type="Shield",
                user="(see log file)",
                action=f"Event log: {lg.get('EventType', '')}",
                timestamp=lg.get("LogDate", ""),
                detail=f"Log size: {lg.get('LogFileLength', 0):,} bytes",
            ))
    except Exception:
        pass  # Shield not licensed — skip silently

    # Sort newest first
    def sort_key(e: DataEvent):
        try:
            ts = e.timestamp.replace("Z", "+00:00").replace("+0000", "+00:00")
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    events.sort(key=sort_key, reverse=True)
    return events


def get_data_activity_findings(sf_client) -> list[Finding]:
    """Health findings from data activity — flags unusual export or bulk patterns."""
    findings: list[Finding] = []
    events = get_data_events(sf_client, days=90)

    export_events = [e for e in events if e.event_type == "Export/Import"]
    batch_events  = [e for e in events if e.event_type == "Batch Job"]
    shield_events = [e for e in events if e.event_type == "Shield"]

    if export_events:
        from collections import Counter
        by_user = Counter(e.user for e in export_events)
        lines = "\n".join(
            f"{user} — {count} export/import action(s)"
            for user, count in by_user.most_common(10)
        )
        findings.append(Finding(
            category="Data Activity",
            severity="Warning",
            title=f"{len(export_events)} data export/import action(s) in last 90 days",
            detail=lines,
            recommendation=(
                "Review these export events in SetupAuditTrail to ensure they were authorized. "
                "Unexpected exports may indicate data exfiltration risk."
            ),
        ))

    if batch_events:
        errors = [e for e in batch_events if "error" in e.detail.lower() and "errors: 0" not in e.detail.lower()]
        if errors:
            lines = "\n".join(f"{e.user} — {e.action} ({e.detail})" for e in errors[:10])
            findings.append(Finding(
                category="Data Activity",
                severity="Warning",
                title=f"{len(errors)} batch job(s) completed with errors in last 90 days",
                detail=lines,
                recommendation=(
                    "Batch jobs with errors may indicate data quality issues or broken integrations. "
                    "Review the Apex Job Queue in Setup."
                ),
            ))

    if shield_events:
        findings.append(Finding(
            category="Data Activity",
            severity="Info",
            title=f"{len(shield_events)} Shield Event Log file(s) available",
            detail="\n".join(f"{e.action} on {e.timestamp[:10]}" for e in shield_events[:10]),
            recommendation=(
                "Salesforce Shield Event Monitoring is active. "
                "Download log files to review detailed user data access patterns."
            ),
        ))

    return findings
