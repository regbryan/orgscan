from datetime import datetime, timedelta, timezone
from checks import Finding

STALE_DAYS = 180  # 6 months

REPORT_SOQL = (
    "SELECT Id, Name, FolderName, LastRunDate "
    "FROM Report "
    "ORDER BY LastRunDate ASC NULLS FIRST "
    "LIMIT 500"
)

DASHBOARD_SOQL = (
    "SELECT Id, Title, FolderName, LastModifiedDate, LastViewedDate "
    "FROM Dashboard "
    "ORDER BY LastViewedDate ASC NULLS FIRST "
    "LIMIT 500"
)


def _fmt_date(iso_str: str | None) -> str:
    if not iso_str:
        return "Never run"
    try:
        dt = datetime.fromisoformat(iso_str.replace("+0000", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return "Unknown"


def check_stale_analytics(sf_client) -> list[Finding]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
    findings = []

    # ── Reports ──────────────────────────────────────────────────
    try:
        reports = sf_client.query(REPORT_SOQL)
        stale_reports = []
        for r in reports:
            last_run = r.get("LastRunDate")
            if last_run is None:
                stale_reports.append((r, None))
            else:
                try:
                    dt = datetime.fromisoformat(last_run.replace("+0000", "+00:00"))
                    if dt < cutoff:
                        stale_reports.append((r, dt))
                except ValueError:
                    stale_reports.append((r, None))

        if stale_reports:
            base_url = sf_client.instance_url if hasattr(sf_client, 'instance_url') else ""
            lines = []
            for r, _ in stale_reports:
                rid = r.get("Id", "")
                name = r.get("Name", "Unknown")
                folder = r.get("FolderName", "Unknown folder")
                last = _fmt_date(r.get("LastRunDate"))
                lines.append(f"{name} ({folder}) — {last}")
            findings.append(Finding(
                category="Analytics",
                severity="Info",
                title=f"{len(stale_reports)} report(s) not run in {STALE_DAYS}+ days",
                detail="\n".join(lines),
                recommendation=(
                    "Review these reports in Setup → Reports. Delete or archive unused reports "
                    "to reduce clutter and improve performance."
                ),
                link=sf_client.sf_url("/lightning/o/Report/home") if hasattr(sf_client, 'sf_url') else None,
            ))
    except Exception:
        pass

    # ── Dashboards ────────────────────────────────────────────────
    try:
        dashboards = sf_client.query(DASHBOARD_SOQL)
        stale_dash = []
        for d in dashboards:
            last_viewed = d.get("LastViewedDate")
            if last_viewed is None:
                stale_dash.append((d, None))
            else:
                try:
                    dt = datetime.fromisoformat(last_viewed.replace("+0000", "+00:00"))
                    if dt < cutoff:
                        stale_dash.append((d, dt))
                except ValueError:
                    stale_dash.append((d, None))

        if stale_dash:
            lines = []
            for d, _ in stale_dash:
                title = d.get("Title", "Unknown")
                folder = d.get("FolderName", "Unknown folder")
                last = _fmt_date(d.get("LastViewedDate"))
                lines.append(f"{title} ({folder}) — Last viewed: {last}")
            findings.append(Finding(
                category="Analytics",
                severity="Info",
                title=f"{len(stale_dash)} dashboard(s) not viewed in {STALE_DAYS}+ days",
                detail="\n".join(lines),
                recommendation=(
                    "Review these dashboards. Delete or move unused dashboards to a retirement folder "
                    "to keep the org clean."
                ),
                link=sf_client.sf_url("/lightning/o/Dashboard/home") if hasattr(sf_client, 'sf_url') else None,
            ))
    except Exception:
        pass

    return findings
