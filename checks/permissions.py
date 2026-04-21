from checks import Finding

# Step 1: fetch permission sets + their ProfileId
PSET_SOQL = (
    "SELECT Id, Name, Label, IsOwnedByProfile, ProfileId, "
    "PermissionsModifyAllData, PermissionsViewAllData "
    "FROM PermissionSet"
)

# Step 2: resolve profile names in bulk
PROFILE_SOQL = "SELECT Id, Name FROM Profile"

# Profile names where elevated permissions are expected
_ADMIN_KEYWORDS = ("administrator", "system admin", "sysadmin")


def _is_admin_profile(name: str) -> bool:
    return any(kw in name.lower() for kw in _ADMIN_KEYWORDS)


def check_excessive_permissions(sf_client) -> list[Finding]:
    # Fetch all permission sets
    records = sf_client.query(PSET_SOQL)

    # Build a Profile ID → Name map (separate query, guaranteed to work)
    profile_map: dict[str, str] = {}
    try:
        profiles = sf_client.query(PROFILE_SOQL)
        profile_map = {p["Id"]: p["Name"] for p in profiles if p.get("Id")}
    except Exception:
        pass

    findings = []
    for r in records:
        is_profile_owned = bool(r.get("IsOwnedByProfile"))
        profile_id = r.get("ProfileId") or ""
        profile_name = profile_map.get(profile_id, "")

        # Build human-readable display name
        if is_profile_owned and profile_name:
            display = f"Profile: {profile_name}"
        elif is_profile_owned:
            display = f"Profile: {r.get('Label') or r.get('Name') or 'Unknown'}"
        else:
            display = f"Permission Set: {r.get('Label') or r.get('Name') or 'Unknown'}"

        # Determine severity
        if not is_profile_owned:
            sev = "Critical"   # standalone perm set with escalated perms = unexpected
        elif profile_name and _is_admin_profile(profile_name):
            sev = "Info"       # System Administrator having Modify All = expected
        else:
            sev = "Warning"    # non-admin profile with elevated perms = worth reviewing

        # Build a direct link to the profile or permission set
        record_id = profile_id if is_profile_owned else (r.get("Id") or "")
        if is_profile_owned and record_id:
            rec_link = sf_client.sf_url(f"/lightning/setup/Profiles/page?address=/{record_id}")
        elif record_id:
            rec_link = sf_client.sf_url(f"/lightning/setup/PermSets/page?address=/{record_id}")
        else:
            rec_link = ""

        if r.get("PermissionsModifyAllData"):
            findings.append(Finding(
                category="Permissions",
                severity=sev,
                title="Modify All Data is enabled",
                detail=display,
                recommendation="Remove Modify All Data unless this profile absolutely requires it.",
                link=rec_link,
            ))
        if r.get("PermissionsViewAllData"):
            findings.append(Finding(
                category="Permissions",
                severity=sev,
                title="View All Data is enabled",
                detail=display,
                recommendation="Remove View All Data unless strictly necessary for this profile.",
                link=rec_link,
            ))

    return findings
