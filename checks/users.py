from datetime import datetime, timedelta, timezone
from checks import Finding

INACTIVE_DAYS = 90
SOQL = (
    "SELECT Name, Username, LastLoginDate FROM User "
    "WHERE IsActive = true AND Profile.UserLicense.LicenseDefinitionKey != 'PID_Guest'"
)


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

    names = ", ".join(f"{r['Name']} ({r['Username']})" for r in inactive)
    return [
        Finding(
            category="Users",
            severity="Critical",
            title=f"{len(inactive)} user(s) inactive 90+ days but consuming licenses",
            detail=names,
            recommendation="Deactivate these users or reassign their licenses to reduce costs.",
        )
    ]
