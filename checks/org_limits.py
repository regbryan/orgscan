"""
Org Configuration & Limits
Checks: edition type, storage usage (data + file), API call consumption,
governor limit snapshot, and sandbox availability / status.
"""
from checks import Finding


def check_org_limits(sf_client) -> list[Finding]:
    findings = []

    # ── Organization record: edition + storage ───────────────────────────────
    try:
        orgs = sf_client.query(
            "SELECT Name, OrganizationType, IsSandbox, "
            "DataStorageMB, UsedDataStorageMB, FileStorageMB, UsedFileStorageMB "
            "FROM Organization"
        )
        if orgs:
            org = orgs[0]
            for label, used_key, total_key in [
                ("Data storage", "UsedDataStorageMB", "DataStorageMB"),
                ("File storage", "UsedFileStorageMB", "FileStorageMB"),
            ]:
                total = org.get(total_key) or 0
                used  = org.get(used_key)  or 0
                if total > 0:
                    pct = (used / total) * 100
                    if pct >= 90:
                        findings.append(Finding(
                            category="Org Config",
                            severity="Critical",
                            title=f"{label} at {pct:.0f}% capacity",
                            detail=f"{used:,} MB used of {total:,} MB ({pct:.1f}%)",
                            recommendation=(
                                "Immediately delete unused records and files, archive old data, "
                                "or purchase additional storage to avoid write failures."
                            ),
                        ))
                    elif pct >= 75:
                        findings.append(Finding(
                            category="Org Config",
                            severity="Warning",
                            title=f"{label} at {pct:.0f}% capacity",
                            detail=f"{used:,} MB used of {total:,} MB ({pct:.1f}%)",
                            recommendation=(
                                "Plan a data cleanup or archive project. "
                                "At 90%+ Salesforce blocks new record creation."
                            ),
                        ))
    except Exception:
        pass

    # ── REST /limits: daily API call consumption ─────────────────────────────
    try:
        limits = sf_client.rest_get("limits")

        api = limits.get("DailyApiRequests", {})
        max_api  = api.get("Max", 0)
        rem_api  = api.get("Remaining", max_api)
        used_api = max_api - rem_api
        if max_api > 0:
            pct = (used_api / max_api) * 100
            if pct >= 75:
                sev = "Critical" if pct >= 90 else "Warning"
                findings.append(Finding(
                    category="Org Config",
                    severity=sev,
                    title=f"Daily API calls at {pct:.0f}% of limit",
                    detail=f"{used_api:,} of {max_api:,} daily API requests used today",
                    recommendation=(
                        "Identify high-frequency integrations and switch them to bulk/streaming APIs. "
                        "Consider upgrading the API call limit."
                    ),
                ))

        # Concurrent REST limit
        conc = limits.get("ConcurrentAsyncGetReportInstances", {})
        max_conc = conc.get("Max", 0)
        rem_conc = conc.get("Remaining", max_conc)
        if max_conc > 0 and rem_conc == 0:
            findings.append(Finding(
                category="Org Config",
                severity="Warning",
                title="Concurrent async report instance limit reached",
                detail=f"All {max_conc} concurrent report instance slots are in use",
                recommendation=(
                    "Reduce concurrent report executions or schedule reports during off-peak hours."
                ),
            ))
    except Exception:
        pass

    # ── Sandboxes (production orgs only — Tooling API) ───────────────────────
    try:
        sandboxes = sf_client.tooling_query(
            "SELECT Id, SandboxName, Status, LicenseType FROM SandboxInfo ORDER BY SandboxName"
        )
        failed = [s["SandboxName"] for s in sandboxes if s.get("Status") == "Failed"]
        if failed:
            findings.append(Finding(
                category="Org Config",
                severity="Warning",
                title=f"{len(failed)} sandbox(es) in Failed state",
                detail=", ".join(failed),
                recommendation=(
                    "Refresh or delete failed sandboxes. "
                    "Failed sandboxes occupy license capacity and cannot be used for testing."
                ),
                link=sf_client.sf_url("/lightning/setup/SandboxPage/home"),
            ))
        elif sandboxes:
            # Surface sandbox inventory as info
            lines = "\n".join(
                f"{s.get('SandboxName', '?')} — {s.get('Status', '?')} ({s.get('LicenseType', '?')})"
                for s in sandboxes
            )
            findings.append(Finding(
                category="Org Config",
                severity="Info",
                title=f"{len(sandboxes)} sandbox environment(s) available",
                detail=lines,
                recommendation=(
                    "Ensure sandboxes are refreshed regularly and are being used. "
                    "Unused sandboxes should be deleted to free capacity."
                ),
                link=sf_client.sf_url("/lightning/setup/SandboxPage/home"),
            ))
    except Exception:
        pass  # Not a production org or access restricted

    return findings
