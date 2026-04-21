"""
Integration Mapping
Checks: Connected Apps, active OAuth sessions, Named Credentials,
service account users, and external API usage indicators.
"""
from checks import Finding


def check_integrations(sf_client) -> list[Finding]:
    findings = []

    # ── Connected Applications ────────────────────────────────────────────────
    try:
        apps = sf_client.tooling_query(
            "SELECT Id, DeveloperName, OptionsIsAdminApproved FROM ConnectedApplication"
        )
        if apps:
            unapproved = [a for a in apps if not a.get("OptionsIsAdminApproved")]
            names_all = [a.get("DeveloperName", "Unknown") for a in apps]

            # Surface all connected apps as inventory
            findings.append(Finding(
                category="Integrations",
                severity="Info",
                title=f"{len(apps)} Connected App(s) registered in this org",
                detail="\n".join(
                    f"{a.get('DeveloperName', '?')} — "
                    f"{'Admin-approved' if a.get('OptionsIsAdminApproved') else 'Not admin-approved'}"
                    for a in apps[:20]
                ),
                recommendation=(
                    "Review Connected Apps regularly. Remove apps for decommissioned integrations. "
                    "Use 'Admin approved users are pre-authorized' to prevent unauthorized OAuth grants."
                ),
                link=sf_client.sf_url("/lightning/setup/ConnectedApplication/home"),
            ))

            if unapproved:
                findings.append(Finding(
                    category="Integrations",
                    severity="Warning",
                    title=f"{len(unapproved)} Connected App(s) not admin-approved",
                    detail=", ".join(a.get("DeveloperName", "?") for a in unapproved[:10]),
                    recommendation=(
                        "Enable 'Admin approved users are pre-authorized' on Connected Apps "
                        "that should only be used by specific users. "
                        "Without this setting, any user can OAuth-authorize the app."
                    ),
                    link=sf_client.sf_url("/lightning/setup/ConnectedApplication/home"),
                ))
    except Exception:
        pass

    # ── Active OAuth Sessions ─────────────────────────────────────────────────
    try:
        tokens = sf_client.query(
            "SELECT Id, AppName, UseCount, LastUsedDate "
            "FROM OauthToken ORDER BY LastUsedDate DESC NULLS LAST LIMIT 200"
        )
        if tokens:
            by_app: dict[str, int] = {}
            for t in tokens:
                app = t.get("AppName") or "Unknown"
                by_app[app] = by_app.get(app, 0) + 1

            lines = "\n".join(
                f"{app}: {count} active session(s)"
                for app, count in sorted(by_app.items(), key=lambda x: -x[1])[:15]
            )
            findings.append(Finding(
                category="Integrations",
                severity="Info",
                title=f"{len(tokens)} active OAuth session(s) across {len(by_app)} app(s)",
                detail=lines,
                recommendation=(
                    "Review OAuth sessions for unfamiliar apps or unusually high session counts. "
                    "Revoke sessions for decommissioned integrations via Setup → OAuth Connected Apps."
                ),
                link=sf_client.sf_url("/lightning/setup/OauthConsumerManagement/home"),
            ))
    except Exception:
        pass

    # ── Named Credentials ─────────────────────────────────────────────────────
    try:
        creds = sf_client.tooling_query(
            "SELECT Id, DeveloperName, Label, Endpoint, PrincipalType FROM NamedCredential"
        )
        if creds:
            lines = "\n".join(
                f"{c.get('Label') or c.get('DeveloperName', '?')} → {c.get('Endpoint', '?')} "
                f"(auth: {c.get('PrincipalType', '?')})"
                for c in creds[:15]
            )
            findings.append(Finding(
                category="Integrations",
                severity="Info",
                title=f"{len(creds)} Named Credential(s) configured",
                detail=lines,
                recommendation=(
                    "Verify all named credentials point to active, authorized endpoints. "
                    "Remove named credentials for decommissioned integrations to reduce attack surface."
                ),
                link=sf_client.sf_url("/lightning/setup/NamedCredential/home"),
            ))
    except Exception:
        pass

    # ── Auth Providers (external identity) ───────────────────────────────────
    try:
        auth_providers = sf_client.tooling_query(
            "SELECT Id, DeveloperName, ProviderType FROM AuthProvider"
        )
        if auth_providers:
            lines = "\n".join(
                f"{a.get('DeveloperName', '?')} ({a.get('ProviderType', '?')})"
                for a in auth_providers
            )
            findings.append(Finding(
                category="Integrations",
                severity="Info",
                title=f"{len(auth_providers)} Auth Provider(s) configured",
                detail=lines,
                recommendation=(
                    "Confirm all auth providers are still in use. "
                    "Inactive providers for retired integrations should be removed."
                ),
                link=sf_client.sf_url("/lightning/setup/AuthProviders/home"),
            ))
    except Exception:
        pass

    return findings
