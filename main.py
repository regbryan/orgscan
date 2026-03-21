"""
OrgScan — FastAPI entry point.

Active org and findings are tracked in module-level variables (single-user, in-memory).
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import ai_describer
import report as report_module
from checks import Finding
from checks.users import check_inactive_users
from checks.flows import check_flows
from checks.fields import check_unused_fields
from checks.permissions import check_excessive_permissions
from checks.validation_rules import check_validation_rules
from checks.activity import get_activity_findings, get_activity_log
from score import compute_score
from sf_client import SalesforceClient

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="OrgScan")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Server-side state
_active_org: dict | None = None
_active_findings: list[Finding] | None = None
_active_score: int = 100
_flow_descriptions: list[dict] = []


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# --- Orgs ---

@app.get("/orgs")
def list_orgs():
    return auth.list_orgs()


@app.post("/orgs/connect")
def orgs_connect():
    url = auth.get_auth_url()
    return {"auth_url": url}


@app.get("/orgs/callback", response_class=HTMLResponse)
def orgs_callback(code: str, state: str = ""):
    try:
        token_data = auth.exchange_code(code, state=state)
        auth.store_token_response(token_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return HTMLResponse('<script>window.location="/"</script>')


@app.delete("/orgs/{org_id}")
def delete_org(org_id: str):
    auth.remove_org(org_id)
    return {"status": "ok"}


# --- Scan ---

class ScanRequest(BaseModel):
    org_id: str


@app.post("/scan")
def scan(body: ScanRequest):
    global _active_org, _active_findings, _active_score, _flow_descriptions

    org = auth.get_org(body.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found. Connect it first.")

    sf = SalesforceClient(org)
    _active_org = {**org, "org_id": body.org_id}
    _flow_descriptions = []

    findings: list[Finding] = []
    check_fns = [
        check_inactive_users,
        check_flows,
        check_unused_fields,
        check_excessive_permissions,
        check_validation_rules,
        get_activity_findings,
    ]
    for fn in check_fns:
        try:
            findings.extend(fn(sf))
        except Exception as e:
            findings.append(Finding(
                category="System",
                severity="Info",
                title=f"Check failed: {fn.__name__}",
                detail=str(e),
                recommendation="Check your org connection and permissions.",
            ))

    _active_findings = findings
    _active_score = compute_score(findings)
    return {"findings": [vars(f) for f in findings], "score": _active_score}


@app.get("/findings")
def get_findings():
    findings = _active_findings or []
    return {"findings": [vars(f) for f in findings], "score": _active_score}


@app.get("/activity")
def get_activity(days: int = 30):
    if not _active_org:
        raise HTTPException(status_code=400, detail="No org connected")
    client = SalesforceClient(_active_org)
    events = get_activity_log(client, days=days)
    return {"events": [
        {
            "event_type": e.event_type,
            "user": e.user,
            "action": e.action,
            "timestamp": e.timestamp,
            "ip_address": e.ip_address,
            "status": e.status,
        }
        for e in events
    ]}


# --- Flow AI Describe ---

@app.post("/flows/{flow_id}/describe")
def describe_flow(flow_id: str):
    if _active_org is None:
        raise HTTPException(status_code=404, detail="No active org. Run a scan first.")
    try:
        sf = SalesforceClient(_active_org)
        flow_xml = sf.get_flow_xml(flow_id)
        description = ai_describer.generate_flow_description(flow_xml)
        return {"description": description}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


class WriteDescriptionRequest(BaseModel):
    description: str


@app.post("/flows/{flow_id}/write-description")
def write_flow_description(flow_id: str, body: WriteDescriptionRequest):
    if _active_org is None:
        raise HTTPException(status_code=404, detail="No active org. Run a scan first.")
    try:
        sf = SalesforceClient(_active_org)
        sf.write_flow_description(flow_id, body.description)
        _flow_descriptions.append({"flow_name": flow_id, "description": body.description})
        if _active_findings:
            for f in _active_findings:
                if f.flow_api_name == flow_id and "description" in f.title.lower():
                    f.severity = "Resolved"
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- Report ---

class ReportRequest(BaseModel):
    client_name: str


@app.post("/report")
def generate_report(body: ReportRequest):
    if _active_findings is None:
        raise HTTPException(status_code=404, detail="No findings yet. Run a scan first.")
    try:
        narrative = ai_describer.generate_org_narrative(_active_findings, _active_score)
    except Exception:
        narrative = "Org health assessment complete. Please review the findings below."

    branding = report_module.load_branding()
    pdf_bytes = report_module.generate_pdf(
        client_name=body.client_name,
        findings=_active_findings,
        score=_active_score,
        narrative=narrative,
        branding=branding,
        flow_descriptions=_flow_descriptions,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="orgscan-{body.client_name}.pdf"'},
    )
