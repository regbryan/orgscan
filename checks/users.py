from datetime import datetime, timedelta, timezone
from checks import Finding

INACTIVE_DAYS = 90
SOQL = (
    "SELECT Id, Name, Username, LastLoginDate FROM User "
    "WHERE IsActive = true AND Profile.UserLicense.LicenseDefinitionKey != 'PID_Guest'"
)

_SYSADMIN_WARN_THRESHOLD = 5  # Flag if more than this many sysadmins


def check_inactive_users(sf_client) -> list[Finding]:
    records = sf_client.query(SOQL)
    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)
    inactive = []

    for r in records:
        last_login = r.get("LastLoginDate")
        if last_login is None:
            inactive.append(r)
            continue
        try:
            dt = datetime.fromisoformat(last_login.replace("+0000", "+00:00"))
        except ValueError:
            inactive.append(r)
            continue
        if dt < cutoff:
            inactive.append(r)

    if not inactive:
        return []

    def _fmt_last_login(iso_str):
        if not iso_str:
            return "Never logged in"
        try:
            dt = datetime.fromisoformat(iso_str.replace("+0000", "+00:00"))
            return "Last login: " + dt.strftime("%b %d, %Y")
        except ValueError:
            return "Last login: unknown"

    findings = []
    for r in inactive:
        user_id = r.get("Id", "")
        user_link = sf_client.sf_url(f"/lightning/r/User/{user_id}/view") if user_id else ""
        findings.append(Finding(
            category="Users",
            severity="Critical",
            title=f"{r['Name']} ({r['Username']}) — inactive 90+ days",
            detail=_fmt_last_login(r.get("LastLoginDate")),
            recommendation="Deactivate this user or reassign their license to reduce costs.",
            link=user_link,
        ))
    return findings


def check_sysadmin_overuse(sf_client) -> list[Finding]:
    """Flag orgs where too many users have the System Administrator profile."""
    try:
        sysadmins = sf_client.query(
            "SELECT Id, Name, Username, LastLoginDate FROM User "
            "WHERE IsActive = true AND Profile.Name = 'System Administrator'"
        )
    except Exception:
        return []

    if not sysadmins:
        return []

    count = len(sysadmins)
    names = "\n".join(
        f"{u.get('Name', '?')} ({u.get('Username', '?')})" for u in sysadmins[:20]
    )

    severity = "Critical" if count > 10 else ("Warning" if count > _SYSADMIN_WARN_THRESHOLD else "Info")

    return [Finding(
        category="Users",
        severity=severity,
        title=f"{count} active user(s) with System Administrator profile",
        detail=names,
        recommendation=(
            "System Administrators have access to all data and settings. "
            "Limit sysadmin access to 1–3 trusted admins. "
            "Use custom profiles or permission sets with least-privilege access for everyone else."
        ),
        link=sf_client.sf_url("/lightning/setup/ManageUsers/home"),
    )]


def check_frozen_users(sf_client) -> list[Finding]:
    """Find users that are frozen (locked out) but still active — these may be security incidents."""
    try:
        frozen = sf_client.query(
            "SELECT Id, UserId FROM UserLogin WHERE IsFrozen = true"
        )
    except Exception:
        return []

    if not frozen:
        return []

    frozen_ids = [u.get("UserId") for u in frozen if u.get("UserId")]
    if not frozen_ids:
        return []

    # Fetch user details for frozen accounts
    try:
        id_list = "','".join(frozen_ids[:50])
        users = sf_client.query(
            f"SELECT Id, Name, Username, IsActive FROM User WHERE Id IN ('{id_list}')"
        )
    except Exception:
        users = []

    active_frozen = [u for u in users if u.get("IsActive")]
    all_frozen_count = len(frozen_ids)

    lines = "\n".join(
        f"{u.get('Name', '?')} ({u.get('Username', '?')}) — Active but frozen"
        for u in active_frozen[:15]
    )
    if not lines:
        lines = f"{all_frozen_count} frozen user account(s) found"

    return [Finding(
        category="Users",
        severity="Warning",
        title=f"{all_frozen_count} frozen user account(s)",
        detail=lines,
        recommendation=(
            "Frozen users are locked out but their account remains active. "
            "Investigate why these accounts are frozen — it may indicate a security incident. "
            "Deactivate accounts that should be permanently disabled."
        ),
        link=sf_client.sf_url("/lightning/setup/ManageUsers/home"),
    )]
