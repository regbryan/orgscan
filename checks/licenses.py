"""
License Utilization
Checks: purchased vs. assigned vs. active licenses, license type breakdown,
inactive users consuming paid seats, and unassigned licenses.
"""
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from checks import Finding


# License definition keys to skip (community/guest/partner — typically cheap/free)
_SKIP_KEYS = {
    "PID_Guest", "PID_Partner_Community", "PID_Customer_Community",
    "PID_Partner_Portal", "PID_Customer_Portal",
}

# License names where 100% utilization is normal/expected — integration
# and system licenses that are bought to match a specific need.
# These should never be Critical, at most Info.
_INTEGRATION_LICENSES = {
    "Analytics Cloud Integration User",
    "Salesforce Integration",
    "Identity",
    "External Identity",
    "Authenticated Website",
    "Work.com Only",
    "High Volume Customer Portal",
    "Service Cloud Portal",
}

_INACTIVE_DAYS = 90

# Plain-English descriptions for common Salesforce license types
_LICENSE_DESC: dict[str, str] = {
    "Salesforce": "Full CRM access — Sales Cloud, Service Cloud, custom objects, reports, dashboards, and API.",
    "Salesforce Platform": "Custom apps and objects only — no standard Sales/Service Cloud features.",
    "Force.com - App Subscription": "Legacy platform license for custom app access with limited standard objects.",
    "Force.com - One App": "Single custom app access with read-only on Accounts and Contacts.",
    "Identity": "SSO and identity services only — no CRM data access.",
    "Knowledge Only": "Read/write access to Knowledge articles only.",
    "Chatter Free": "Chatter social collaboration — no CRM record access.",
    "Chatter External": "Chatter access for external users (customers/partners).",
    "Chatter Plus": "Chatter plus read access to Accounts, Contacts, and custom objects.",
    "Company Community": "Internal community portal access for employees.",
    "Customer Community": "External community portal for customers — limited data access.",
    "Customer Community Plus": "Enhanced community access with reports, dashboards, and more objects.",
    "Partner Community": "Partner portal access with lead and opportunity management.",
    "Customer Community Plus Login": "Per-login version of Customer Community Plus.",
    "Customer Community Login": "Per-login version of Customer Community.",
    "Partner Community Login": "Per-login version of Partner Community.",
    "Salesforce Integration": "API-only access for system integrations — no UI login.",
    "Analytics Cloud - Wave Analytics": "Tableau CRM (formerly Wave) for advanced analytics and dashboards.",
    "Work.com Only": "Work.com features for employee engagement and performance.",
    "High Volume Customer Portal": "High-volume portal for self-service customer communities.",
    "Authenticated Website": "Access to authenticated Experience Cloud sites.",
    "External Identity": "Identity verification and login for external users.",
    "Service Cloud Portal": "Customer self-service portal for case management.",
}


def _license_description(name: str) -> str:
    """Return a brief description for a license type, or a generic fallback."""
    if name in _LICENSE_DESC:
        return _LICENSE_DESC[name]
    lower = name.lower()
    if "platform" in lower:
        return "Platform license — custom apps and limited standard object access."
    if "community" in lower or "portal" in lower:
        return "Community/portal license for external or limited internal users."
    if "chatter" in lower:
        return "Chatter collaboration license — social features only."
    if "identity" in lower:
        return "Identity/SSO license — authentication services."
    return ""


def check_licenses(sf_client) -> list[Finding]:
    findings = []

    # ── UserLicense: purchased vs. used ──────────────────────────────────────
    try:
        licenses = sf_client.query(
            "SELECT Id, Name, TotalLicenses, UsedLicenses, LicenseDefinitionKey "
            "FROM UserLicense ORDER BY TotalLicenses DESC"
        )
        total_purchased = 0
        total_used      = 0

        for lic in licenses:
            key   = lic.get("LicenseDefinitionKey", "")
            if key in _SKIP_KEYS:
                continue
            total = lic.get("TotalLicenses") or 0
            used  = lic.get("UsedLicenses")  or 0
            name  = lic.get("Name") or "Unknown"
            if total <= 0:
                continue

            total_purchased += total
            total_used      += used
            pct = (used / total) * 100

            desc = _license_description(name)
            desc_line = f"\n{desc}" if desc else ""
            is_integration = name in _INTEGRATION_LICENSES

            # Integration/system licenses at capacity is normal — downgrade to Info
            if is_integration and pct >= 85:
                findings.append(Finding(
                    category="Licenses",
                    severity="Info",
                    title=f"{name} — {pct:.0f}% of licenses assigned ({used}/{total})",
                    detail=f"{total - used} seat(s) remaining\nThis is a system/integration license — full utilization is expected{desc_line}",
                    recommendation=(
                        "No action needed unless you plan to add more integrations. "
                        "Purchase additional licenses only if expanding."
                    ),
                    link=sf_client.sf_url("/lightning/setup/CompanyProfilePage/home"),
                ))
            elif pct >= 95:
                findings.append(Finding(
                    category="Licenses",
                    severity="Critical",
                    title=f"{name} — {pct:.0f}% of licenses assigned ({used}/{total})",
                    detail=f"{total - used} seat(s) remaining{desc_line}",
                    recommendation=(
                        "You are at capacity. Deactivate unused users before onboarding new ones, "
                        "or purchase additional licenses immediately."
                    ),
                    link=sf_client.sf_url("/lightning/setup/CompanyProfilePage/home"),
                ))
            elif pct >= 85:
                findings.append(Finding(
                    category="Licenses",
                    severity="Warning",
                    title=f"{name} — {pct:.0f}% of licenses assigned ({used}/{total})",
                    detail=f"{total - used} seat(s) remaining{desc_line}",
                    recommendation=(
                        "License capacity is getting tight. Review inactive users "
                        "and plan for additional licenses if growth is expected."
                    ),
                    link=sf_client.sf_url("/lightning/setup/CompanyProfilePage/home"),
                ))
            elif used == 0:
                findings.append(Finding(
                    category="Licenses",
                    severity="Info",
                    title=f"{name} — {total} license(s) purchased, none assigned",
                    detail=f"No users are assigned this license type{desc_line}",
                    recommendation=(
                        "Confirm whether these licenses are still needed. "
                        "Unused licenses represent unnecessary recurring cost."
                    ),
                    link=sf_client.sf_url("/lightning/setup/CompanyProfilePage/home"),
                ))
    except Exception:
        pass

    # ── Active users on paid licenses who haven't logged in 90+ days ─────────
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=_INACTIVE_DAYS)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        inactive = sf_client.query(
            f"SELECT Id, Name, Username, LastLoginDate, Profile.UserLicense.Name "
            f"FROM User "
            f"WHERE IsActive = true "
            f"AND Profile.UserLicense.LicenseDefinitionKey NOT IN "
            f"('PID_Guest', 'PID_Partner_Community', 'PID_Customer_Community') "
            f"AND (LastLoginDate < {cutoff} OR LastLoginDate = null)"
        )
        if inactive:
            by_lic: dict[str, list] = defaultdict(list)
            for u in inactive:
                lic_name = ""
                profile = u.get("Profile")
                if isinstance(profile, dict):
                    ul = profile.get("UserLicense")
                    if isinstance(ul, dict):
                        lic_name = ul.get("Name", "")
                by_lic[lic_name or "Unknown"].append(u)

            lines = "\n".join(
                f"{lic}: {len(users)} user(s) inactive 90+ days"
                for lic, users in sorted(by_lic.items(), key=lambda x: -len(x[1]))
            )
            findings.append(Finding(
                category="Licenses",
                severity="Warning",
                title=f"{len(inactive)} active user(s) on paid licenses, inactive 90+ days",
                detail=lines,
                recommendation=(
                    "Deactivate these users to free paid license seats. "
                    "Former employees and departed contractors sitting on active licenses "
                    "are a common cost leak and a security risk."
                ),
                link=sf_client.sf_url("/lightning/setup/ManageUsers/home"),
            ))
    except Exception:
        pass

    return findings
