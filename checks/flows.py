from checks import Finding

# FlowDefinition = one record per flow (the "container").
# ActiveVersionId != null means the flow has an active version deployed.
FLOW_DEF_SOQL = (
    "SELECT Id, DeveloperName, Description, ActiveVersionId "
    "FROM FlowDefinition "
    "WHERE ActiveVersionId != null"
)

MIN_API_VERSION = 50


def check_flows(sf_client) -> list[Finding]:
    definitions = sf_client.tooling_query(FLOW_DEF_SOQL)
    findings = []

    # ── API version check (best-effort) ───────────────────────────────────────
    try:
        active_version_ids = [
            d["ActiveVersionId"] for d in definitions if d.get("ActiveVersionId")
        ]
        if active_version_ids:
            id_list = "','".join(active_version_ids)
            versions = sf_client.tooling_query(
                f"SELECT Id, ApiVersion FROM Flow WHERE Id IN ('{id_list}')"
            )
            ver_map = {v["Id"]: v.get("ApiVersion", 0) for v in versions}
            old_api = [
                d for d in definitions
                if ver_map.get(d.get("ActiveVersionId", ""), 99) < MIN_API_VERSION
            ]
            if old_api:
                names = "\n".join(
                    f"{d['DeveloperName']} (API {ver_map.get(d.get('ActiveVersionId',''), '?')})"
                    for d in old_api
                )
                findings.append(Finding(
                    category="Flows",
                    severity="Critical",
                    title=f"{len(old_api)} flow(s) running on API version < {MIN_API_VERSION}",
                    detail=names,
                    recommendation="Upgrade these flows to API version 59.0 in the Flow Builder.",
                ))
    except Exception:
        pass  # Flow version query not available in this org — skip API check

    # ── No description check ───────────────────────────────────────────────────
    no_desc = [d for d in definitions if not d.get("Description")]
    findings.extend(
        Finding(
            category="Flows",
            severity="Warning",
            title="Flow has no description",
            detail=f"{d['DeveloperName']} has no description",
            recommendation="Generate a description with AI using the button below.",
            flow_api_name=d["DeveloperName"],
            link=(
                sf_client.sf_url(
                    f"/builder_platform_interaction/flowBuilder.app?flowId={d['ActiveVersionId']}"
                ) if d.get("ActiveVersionId") else ""
            ),
        )
        for d in no_desc
    )

    return findings


def check_automation_inventory(sf_client) -> list[Finding]:
    """
    Catalog Process Builder flows, Workflow Rules, and Apex Triggers.
    Surfaces inactive automation that may be dead weight, and flags legacy
    Process Builder / Workflow Rules that should be migrated to Flows.
    """
    findings = []

    # ── Process Builder (FlowDefinition with ProcessType = 'Workflow') ────────
    try:
        pb_active = sf_client.tooling_query(
            "SELECT Id, DeveloperName, Description, ActiveVersionId "
            "FROM FlowDefinition WHERE ProcessType = 'Workflow' AND ActiveVersionId != null"
        )
        pb_inactive = sf_client.tooling_query(
            "SELECT Id, DeveloperName FROM FlowDefinition "
            "WHERE ProcessType = 'Workflow' AND ActiveVersionId = null"
        )

        if pb_active:
            names = "\n".join(d.get("DeveloperName", "?") for d in pb_active[:20])
            findings.append(Finding(
                category="Flows",
                severity="Warning",
                title=f"{len(pb_active)} active Process Builder process(es)",
                detail=names,
                recommendation=(
                    "Process Builder is a legacy automation tool. "
                    "Salesforce recommends migrating all Process Builder automations to Flow. "
                    "Use the Flow Migration Tool in Setup to convert them."
                ),
                link=sf_client.sf_url("/lightning/setup/ProcessAutomation/home"),
            ))

        if pb_inactive:
            names = "\n".join(d.get("DeveloperName", "?") for d in pb_inactive[:20])
            findings.append(Finding(
                category="Flows",
                severity="Info",
                title=f"{len(pb_inactive)} inactive Process Builder process(es)",
                detail=names,
                recommendation=(
                    "Inactive Process Builder processes are dead weight. "
                    "Delete them to reduce clutter and avoid confusion."
                ),
                link=sf_client.sf_url("/lightning/setup/ProcessAutomation/home"),
            ))
    except Exception:
        pass

    # ── Workflow Rules ────────────────────────────────────────────────────────
    try:
        wf_active = sf_client.tooling_query(
            "SELECT Id, Name, TableEnumOrId FROM WorkflowRule WHERE Metadata.active = true LIMIT 200"
        )
        wf_inactive = sf_client.tooling_query(
            "SELECT Id, Name, TableEnumOrId FROM WorkflowRule WHERE Metadata.active = false LIMIT 200"
        )

        if wf_active:
            # Group by object
            by_obj: dict[str, int] = {}
            for w in wf_active:
                obj = w.get("TableEnumOrId", "Unknown")
                by_obj[obj] = by_obj.get(obj, 0) + 1
            lines = "\n".join(f"{obj}: {cnt}" for obj, cnt in sorted(by_obj.items(), key=lambda x: -x[1]))
            findings.append(Finding(
                category="Flows",
                severity="Warning",
                title=f"{len(wf_active)} active Workflow Rule(s) — legacy automation",
                detail=lines,
                recommendation=(
                    "Workflow Rules are a legacy automation tool retired by Salesforce. "
                    "Migrate all Workflow Rules to Flow before the retirement deadline."
                ),
                link=sf_client.sf_url("/lightning/setup/WorkflowRules/home"),
            ))

        if wf_inactive:
            names = "\n".join(w.get("Name", "?") for w in wf_inactive[:15])
            findings.append(Finding(
                category="Flows",
                severity="Info",
                title=f"{len(wf_inactive)} inactive Workflow Rule(s)",
                detail=names,
                recommendation=(
                    "Inactive Workflow Rules are clutter. Delete them or migrate to Flow."
                ),
                link=sf_client.sf_url("/lightning/setup/WorkflowRules/home"),
            ))
    except Exception:
        pass

    # ── Apex Triggers ─────────────────────────────────────────────────────────
    try:
        triggers = sf_client.tooling_query(
            "SELECT Id, Name, TableEnumOrId, Status FROM ApexTrigger ORDER BY TableEnumOrId"
        )
        if triggers:
            active_t   = [t for t in triggers if t.get("Status") == "Active"]
            inactive_t = [t for t in triggers if t.get("Status") != "Active"]

            if active_t:
                by_obj: dict[str, list] = {}
                for t in active_t:
                    obj = t.get("TableEnumOrId", "Unknown")
                    by_obj.setdefault(obj, []).append(t.get("Name", "?"))
                lines = "\n".join(
                    f"{obj}: {', '.join(names[:5])}" + (" …" if len(names) > 5 else "")
                    for obj, names in sorted(by_obj.items())
                )
                findings.append(Finding(
                    category="Flows",
                    severity="Info",
                    title=f"{len(active_t)} active Apex Trigger(s) across {len(by_obj)} object(s)",
                    detail=lines,
                    recommendation=(
                        "Review active triggers to ensure each object has at most one trigger "
                        "using a handler pattern. Multiple triggers on the same object have "
                        "unpredictable execution order."
                    ),
                    link=sf_client.sf_url("/lightning/setup/ApexTriggers/home"),
                ))

            if inactive_t:
                names_list = "\n".join(
                    f"{t.get('Name', '?')} ({t.get('TableEnumOrId', '?')}) — {t.get('Status', '?')}"
                    for t in inactive_t[:15]
                )
                findings.append(Finding(
                    category="Flows",
                    severity="Info",
                    title=f"{len(inactive_t)} inactive/invalid Apex Trigger(s)",
                    detail=names_list,
                    recommendation=(
                        "Inactive or invalid triggers are dead code. "
                        "Delete them to reduce confusion and keep the org clean."
                    ),
                    link=sf_client.sf_url("/lightning/setup/ApexTriggers/home"),
                ))
    except Exception:
        pass

    return findings
