from checks import Finding

SOQL = (
    "SELECT Name, PermissionsModifyAllData, PermissionsViewAllData "
    "FROM PermissionSet "
    "WHERE IsOwnedByProfile = false OR IsOwnedByProfile = true"
)


def check_excessive_permissions(sf_client) -> list[Finding]:
    records = sf_client.query(SOQL)
    findings = []

    for r in records:
        name = r.get("Name", "Unknown")
        if r.get("PermissionsModifyAllData"):
            findings.append(Finding(
                category="Permissions",
                severity="Critical",
                title="Profile/Permission Set has Modify All Data",
                detail=f"{name} has PermissionsModifyAllData = true",
                recommendation="Remove Modify All Data unless this profile absolutely requires it.",
            ))
        if r.get("PermissionsViewAllData"):
            findings.append(Finding(
                category="Permissions",
                severity="Critical",
                title="Profile/Permission Set has View All Data",
                detail=f"{name} has PermissionsViewAllData = true",
                recommendation="Remove View All Data unless strictly necessary for this profile.",
            ))

    return findings
