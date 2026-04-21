"""
OrgScan — FastAPI entry point.

Active org and findings are tracked in module-level variables (single-user, in-memory).

Security:
  - Session-based authentication (cookie set after OAuth callback)
  - Rate limiting (per-IP, in-memory)
  - Structured request/error logging
  - Input validation on all path params
  - CORS restricted to same-origin
"""
import csv
import io
import logging
import os
import re
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import ai_describer
import report as report_module
from checks import Finding
from checks.users import check_inactive_users, check_sysadmin_overuse, check_frozen_users
from checks.flows import check_flows, check_automation_inventory
from checks.org_limits import check_org_limits
from checks.licenses import check_licenses
from checks.integrations import check_integrations
from checks.email import check_email, check_email_domain_verification
from checks.data_quality import check_data_quality
from checks.fields import check_unused_fields
from checks.permissions import check_excessive_permissions
from checks.validation_rules import check_validation_rules
from checks.activity import get_activity_findings, get_activity_log
from checks.data_activity import get_data_activity_findings, get_data_events
from checks.layouts import check_unassigned_layouts
from checks.analytics import check_stale_analytics
from checks.duplicates import (
    scan_duplicates_custom, scan_duplicates_native,
    scan_cross_object_leads_contacts,
    merge_url, convert_lead_url,
    SUPPORTED_OBJECTS, CROSS_MATCH_FIELDS,
)
from score import compute_score
from sf_client import SalesforceClient

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("orgscan")

# ── Input validation ─────────────────────────────────────────────────────────
_SAFE_ID = re.compile(r"^[A-Za-z0-9]{15,18}$")  # Salesforce 15/18-char Ids
_SAFE_DEV_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
_SAFE_OBJECT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")


def _validate_sf_id(value: str, label: str = "Id") -> str:
    if not _SAFE_ID.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value!r}")
    return value


def _validate_dev_name(value: str) -> str:
    if not _SAFE_DEV_NAME.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid DeveloperName: {value!r}")
    return value


def _safe_filename(name: str, max_len: int = 50) -> str:
    """Sanitize a string for use in Content-Disposition filenames."""
    return re.sub(r'[^A-Za-z0-9_\- ]', '', name)[:max_len].strip() or "export"


# ── Rate limiter (in-memory, per-IP) ─────────────────────────────────────────
_rate_buckets: dict[str, list[float]] = {}
_RATE_LIMITS = {
    "default": (30, 60),      # 30 requests per 60s
    "scan": (3, 60),           # 3 scans per 60s
    "ai": (5, 60),             # 5 AI calls per 60s
    "delete": (10, 60),        # 10 deletes per 60s
    "auth": (5, 60),           # 5 auth attempts per 60s
}


def _check_rate_limit(request: Request, bucket_name: str = "default") -> None:
    """Raise 429 if the caller exceeds the rate limit for this bucket."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{bucket_name}"
    now = time.time()
    max_requests, window_seconds = _RATE_LIMITS.get(bucket_name, _RATE_LIMITS["default"])
    timestamps = _rate_buckets.get(key, [])
    # Prune old entries
    timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(timestamps) >= max_requests:
        logger.warning("Rate limit exceeded: ip=%s bucket=%s", client_ip, bucket_name)
        raise HTTPException(status_code=429, detail="Too many requests. Please wait and try again.")
    timestamps.append(now)
    _rate_buckets[key] = timestamps


# ── App setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="OrgScan", docs_url=None, redoc_url=None)  # Disable docs in prod

# CORS — restrict to same-origin only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Session management ──────────────────────────────────────────────────────
# A random token is generated on first OAuth callback and stored as a cookie.
# All API endpoints (except /, /static/*, /orgs/connect, /orgs/callback) require it.
_SESSION_COOKIE = "orgscan_session"
_valid_sessions: set[str] = set()

# Public paths that don't require auth
_PUBLIC_PATHS = frozenset({"/", "/orgs/connect", "/orgs/callback"})


def _is_public_path(path: str) -> bool:
    """Check if a request path is public (no auth required)."""
    if path in _PUBLIC_PATHS:
        return True
    if path.startswith("/static/"):
        return True
    return False


def _require_session(request: Request) -> None:
    """Raise 401 if the request doesn't have a valid session cookie."""
    token = request.cookies.get(_SESSION_COOKIE, "")
    if not token or token not in _valid_sessions:
        raise HTTPException(status_code=401, detail="Not authenticated. Connect a Salesforce org first.")


@app.middleware("http")
async def auth_and_logging_middleware(request: Request, call_next):
    """Enforce session auth on protected endpoints + log all requests."""
    start = time.time()

    # Check auth for non-public paths
    path = request.url.path.rstrip("/") or "/"
    if not _is_public_path(path):
        token = request.cookies.get(_SESSION_COOKIE, "")
        if not token or token not in _valid_sessions:
            return Response(
                content='{"detail":"Not authenticated. Connect a Salesforce org first."}',
                status_code=401,
                media_type="application/json",
            )

    response = await call_next(request)

    elapsed = round((time.time() - start) * 1000, 1)
    client_ip = request.client.host if request.client else "?"
    logger.info(
        "%s %s %s %sms ip=%s",
        request.method, request.url.path, response.status_code, elapsed, client_ip,
    )
    return response

# Server-side state
_active_org: dict | None = None
_active_findings: list[Finding] | None = None
_active_score: int = 100
_flow_descriptions: list[dict] = []

# Duplicate management state
_dup_groups: list[dict] = []
_dup_config: dict = {}
_cross_matches: list[dict] = []


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# --- Orgs ---

@app.get("/orgs")
def list_orgs():
    return auth.list_orgs()


@app.post("/orgs/connect")
def orgs_connect(request: Request):
    _check_rate_limit(request, "auth")
    logger.info("OAuth flow initiated")
    url = auth.get_auth_url()
    return {"auth_url": url}


@app.get("/orgs/callback", response_class=HTMLResponse)
def orgs_callback(code: str, state: str = ""):
    try:
        token_data = auth.exchange_code(code, state=state)
        auth.store_token_response(token_data)
    except Exception as e:
        logger.error("OAuth callback failed: %s", e)
        raise HTTPException(status_code=400, detail="Authentication failed. Please try connecting again.")

    # Create a session token and set it as an httponly cookie
    session_token = secrets.token_urlsafe(32)
    _valid_sessions.add(session_token)
    response = HTMLResponse('<script>window.location="/"</script>')
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True when deploying behind HTTPS
        max_age=86400,  # 24 hours
    )
    logger.info("Session created after OAuth callback")
    return response


@app.delete("/orgs/{org_id}")
def delete_org(org_id: str, request: Request):
    _check_rate_limit(request, "auth")
    _validate_sf_id(org_id, "org_id")
    auth.remove_org(org_id)
    return {"status": "ok"}


# --- Scan ---

class ScanRequest(BaseModel):
    org_id: str


@app.post("/scan")
def scan(body: ScanRequest, request: Request):
    _check_rate_limit(request, "scan")
    global _active_org, _active_findings, _active_score, _flow_descriptions

    org = auth.get_org(body.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found. Connect it first.")

    _active_org = {**org, "org_id": body.org_id}
    sf = SalesforceClient(_active_org)
    _flow_descriptions = []

    findings: list[Finding] = []
    check_fns = [
        check_org_limits,
        check_licenses,
        check_inactive_users,
        check_sysadmin_overuse,
        check_frozen_users,
        check_flows,
        check_automation_inventory,
        check_unused_fields,
        check_excessive_permissions,
        check_validation_rules,
        get_activity_findings,
        get_data_activity_findings,
        check_unassigned_layouts,
        check_stale_analytics,
        check_integrations,
        check_email,
        check_email_domain_verification,
        check_data_quality,
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
    # Always recompute score from current findings so formula changes
    # take effect without requiring a new scan.
    score = compute_score(findings) if findings else _active_score
    return {"findings": [vars(f) for f in findings], "score": score}


@app.get("/activity")
def get_activity(days: int = 30):
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
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


@app.get("/data-activity")
def get_data_activity(days: int = 90):
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    if not _active_org:
        raise HTTPException(status_code=400, detail="No org connected")
    client = SalesforceClient(_active_org)
    events = get_data_events(client, days=days)
    return {"events": [
        {
            "event_type": e.event_type,
            "user": e.user,
            "action": e.action,
            "timestamp": e.timestamp,
            "detail": e.detail,
        }
        for e in events
    ]}


# --- Flow AI Describe ---

@app.post("/flows/{flow_id}/describe")
def describe_flow(flow_id: str, request: Request):
    _check_rate_limit(request, "ai")
    _validate_dev_name(flow_id)
    if _active_org is None:
        raise HTTPException(status_code=404, detail="No active org. Run a scan first.")
    try:
        sf = SalesforceClient(_active_org)
        flow_xml = sf.get_flow_xml(flow_id)
        description = ai_describer.generate_flow_description(flow_xml)
        logger.info("AI describe flow=%s", flow_id)
        return {"description": description}
    except Exception as e:
        logger.error("AI describe failed flow=%s err=%s", flow_id, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to generate flow description. Please try again.")


class WriteDescriptionRequest(BaseModel):
    description: str


@app.post("/flows/{flow_id}/write-description")
def write_flow_description(flow_id: str, body: WriteDescriptionRequest, request: Request):
    _check_rate_limit(request, "default")
    _validate_dev_name(flow_id)
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
        logger.error("Write flow description failed flow=%s err=%s", flow_id, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to write description to Salesforce. Please try again.")


# --- Flow Document PDF ---

class FlowDocRequest(BaseModel):
    client_name: str = ""


@app.post("/flows/{flow_id}/document")
def flow_document(flow_id: str, body: FlowDocRequest, request: Request):
    """Generate a client-ready PDF document for a single flow with description, diagram, and recommendations."""
    _check_rate_limit(request, "ai")
    _validate_dev_name(flow_id)
    if _active_org is None:
        raise HTTPException(status_code=404, detail="No active org. Run a scan first.")
    try:
        sf = SalesforceClient(_active_org)
        flow_metadata = sf.get_flow_xml(flow_id)
        doc = ai_describer.generate_flow_document(flow_metadata)
        logger.info("Flow document generated flow=%s", flow_id)

        branding = report_module.load_branding()
        pdf_bytes = report_module.generate_flow_pdf(
            flow_api_name=flow_id,
            flow_label=flow_id.replace("_", " "),
            description=doc["description"],
            configuration=doc.get("configuration", ""),
            components=doc.get("components", ""),
            recommendations=doc["recommendations"],
            diagram_mermaid=doc["diagram"],
            branding=branding,
            client_name=body.client_name,
            structured=doc.get("structured"),
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="flow-{flow_id}.pdf"'},
        )
    except Exception as e:
        logger.error("Flow document failed flow=%s err=%s", flow_id, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to generate flow document. Please try again.")


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
        headers={"Content-Disposition": f'attachment; filename="orgscan-{_safe_filename(body.client_name)}.pdf"'},
    )


# --- CSV Export ---

@app.get("/export/csv")
def export_csv():
    """Export all findings as a CSV spreadsheet for client delivery."""
    if _active_findings is None:
        raise HTTPException(status_code=404, detail="No findings yet. Run a scan first.")

    buf = io.StringIO()
    writer = csv.writer(buf)

    # Header row
    writer.writerow([
        "Category",
        "Severity",
        "Finding",
        "Detail",
        "Recommendation",
        "Salesforce Link",
    ])

    # Data rows — expand multi-line details into the Detail column
    for f in _active_findings:
        writer.writerow([
            f.category,
            f.severity,
            f.title,
            f.detail.replace("\n", " | ") if f.detail else "",
            f.recommendation,
            f.link or "",
        ])

    csv_bytes = buf.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
    org_name = ""
    if _active_org:
        org_name = _safe_filename(_active_org.get("username", "org").split("@")[0])
    filename = f"orgscan-findings-{org_name}.csv" if org_name else "orgscan-findings.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Duplicate Management ---

class DuplicateScanRequest(BaseModel):
    object_name: str
    match_fields: list[str] = []
    mode: str = "custom"   # "custom" | "native"


@app.get("/duplicates/objects")
def duplicate_objects():
    """Return the list of scannable objects with their available matching fields."""
    objects = [
        {
            "value": name,
            "label": cfg["label"],
            "match_fields": cfg["match_fields"],
            "cross_object": False,
        }
        for name, cfg in SUPPORTED_OBJECTS.items()
    ]
    # Add the cross-object Lead ↔ Contact option
    objects.append({
        "value": "_cross_lead_contact",
        "label": "Lead → Contact (Cross-Object)",
        "match_fields": CROSS_MATCH_FIELDS,
        "cross_object": True,
    })
    return {"objects": objects}


@app.get("/duplicates")
def get_duplicates():
    return {"groups": _dup_groups, "config": _dup_config}


@app.post("/duplicates/scan")
def duplicate_scan(body: DuplicateScanRequest, request: Request):
    _check_rate_limit(request, "scan")
    global _dup_groups, _dup_config

    if not _active_org:
        raise HTTPException(status_code=400, detail="No org connected. Run a scan first.")

    if body.object_name not in SUPPORTED_OBJECTS:
        raise HTTPException(status_code=400, detail=f"Unsupported object: {body.object_name}")

    sf = SalesforceClient(_active_org)

    records_scanned = 0
    try:
        if body.mode == "native":
            groups = scan_duplicates_native(sf, body.object_name)
        else:
            if not body.match_fields:
                raise HTTPException(status_code=400, detail="At least one match field is required.")
            groups, records_scanned = scan_duplicates_custom(sf, body.object_name, body.match_fields)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Duplicate scan failed object=%s err=%s", body.object_name, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Duplicate scan failed. Please try again.")

    # Annotate each group with a Salesforce merge URL
    for g in groups:
        ids = [r["Id"] for r in g["records"] if r.get("Id")]
        g["merge_url"] = merge_url(sf.instance_url, body.object_name, ids[:3])

    _dup_groups = groups
    _dup_config = {
        "object_name": body.object_name,
        "match_fields": body.match_fields,
        "mode": body.mode,
    }

    total_records = sum(g["count"] for g in groups)
    return {
        "groups": groups,
        "total_groups": len(groups),
        "total_records": total_records,
        "records_scanned": records_scanned,
    }


class CrossScanRequest(BaseModel):
    match_fields: list[str]


@app.post("/duplicates/cross-scan")
def cross_scan(body: CrossScanRequest, request: Request):
    """Find unconverted Leads that already have a matching Contact."""
    _check_rate_limit(request, "scan")
    global _cross_matches

    if not _active_org:
        raise HTTPException(status_code=400, detail="No org connected. Run a scan first.")
    if not body.match_fields:
        raise HTTPException(status_code=400, detail="At least one match field is required.")

    sf = SalesforceClient(_active_org)

    try:
        matches, leads_scanned, contacts_scanned = scan_cross_object_leads_contacts(sf, body.match_fields)
    except Exception as e:
        logger.error("Cross-object scan failed err=%s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Cross-object scan failed. Please try again.")

    # Annotate each match with a Convert Lead URL
    for m in matches:
        lead_id = m["lead"].get("Id", "")
        m["convert_url"] = convert_lead_url(sf.instance_url, lead_id) if lead_id else ""

    _cross_matches = matches
    return {
        "matches": matches,
        "total_matches": len(matches),
        "leads_scanned": leads_scanned,
        "contacts_scanned": contacts_scanned,
    }


@app.get("/duplicates/cross-scan")
def get_cross_scan():
    return {"matches": _cross_matches, "total_matches": len(_cross_matches)}


@app.delete("/duplicates/records/{object_name}/{record_id}")
def delete_duplicate_record(object_name: str, record_id: str, request: Request):
    """
    Permanently delete a duplicate record from Salesforce.
    The caller is responsible for choosing which record to delete.
    """
    _check_rate_limit(request, "delete")
    _validate_sf_id(record_id, "record_id")
    global _dup_groups

    if not _active_org:
        raise HTTPException(status_code=400, detail="No org connected.")
    if object_name not in SUPPORTED_OBJECTS:
        raise HTTPException(status_code=400, detail=f"Unsupported object: {object_name}")

    try:
        sf = SalesforceClient(_active_org)
        sf.delete_record(object_name, record_id)
        logger.info("Deleted record object=%s id=%s", object_name, record_id)
    except Exception as e:
        logger.error("Delete failed object=%s id=%s err=%s", object_name, record_id, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to delete record. Please try again.")

    # Remove the deleted record from cached groups
    for g in _dup_groups:
        g["records"] = [r for r in g["records"] if r.get("Id") != record_id]
        g["count"] = len(g["records"])
    _dup_groups = [g for g in _dup_groups if g["count"] >= 2]

    return {"status": "ok", "deleted_id": record_id}
