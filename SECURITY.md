# OrgScan Security Protocol

## Overview

OrgScan connects to Salesforce orgs via OAuth 2.0 and reads/writes org data through the Salesforce REST and Tooling APIs. It also calls the Anthropic API for AI-generated flow descriptions and report narratives. This document describes the security measures in place and how each protocol area is addressed.

---

## 1. Secure Deployment & Monitoring

**Goal:** Enforce HTTPS, store secrets securely, restrict direct database access, and log all authentication attempts, API errors, and unusual traffic.

### What we did

- **Structured request logging** — Every HTTP request is logged with timestamp, method, path, status code, response time (ms), and client IP address. This covers all API calls, static asset requests, and errors.
- **Operation-level logging** — Destructive actions (record deletes, flow description writes) and expensive actions (AI generation, org scans) log specific details including object names, record IDs, flow names, and error messages.
- **Error logging** — All failed Salesforce API calls and Anthropic API calls log the error with context so failures can be traced.
- **No direct database** — OrgScan has no database. All data comes from Salesforce APIs in real time. Token storage uses a local JSON file excluded from version control.
- **HTTPS enforcement** — In production, HTTPS is enforced at the reverse proxy layer (nginx or Caddy). The app itself runs behind the proxy on localhost.

### Log format

```
2026-03-26 14:32:01 INFO [orgscan] POST /scan 200 4523.1ms ip=127.0.0.1
2026-03-26 14:32:05 INFO [orgscan] Deleted record object=Contact id=003xx000004TmKAAU
2026-03-26 14:32:10 WARNING [orgscan] Rate limit exceeded: ip=192.168.1.5 bucket=ai
2026-03-26 14:32:15 ERROR [orgscan] AI describe failed flow=My_Flow err=Connection timeout
```

---

## 2. Prevent Abuse & Bot Attacks

**Goal:** Implement rate limiting for login attempts, API endpoints, account creation, and AI generation requests. Prevent bots or automated scripts from repeatedly calling endpoints or scraping data.

### What we did

- **Per-IP rate limiting** on every endpoint, with tiered limits based on cost and risk:

| Bucket | Limit | Endpoints |
|--------|-------|-----------|
| `auth` | 5 req / 60s | `/orgs/connect` (OAuth initiation) |
| `scan` | 3 req / 60s | `/scan`, `/duplicates/scan`, `/duplicates/cross-scan` |
| `ai` | 5 req / 60s | `/flows/{id}/describe` (Anthropic API calls) |
| `delete` | 10 req / 60s | `DELETE /duplicates/records/{object}/{id}` |
| `default` | 30 req / 60s | All other endpoints |

- **429 Too Many Requests** returned when any limit is exceeded, with a clear error message.
- **Rate limit violations logged** as `WARNING` with the client IP and bucket name so abuse patterns can be detected.
- **API documentation disabled** — `/docs` and `/redoc` endpoints are turned off to prevent automated discovery of the API surface.

### How it works

The rate limiter uses an in-memory sliding window per IP address per bucket. Old timestamps are pruned on each request. No external dependencies required.

---

## 3. Protect Secrets & API Keys

**Goal:** Ensure API keys, database service keys, and tokens are never exposed in frontend code or committed to the repository. All secrets must live in environment variables and only be used server-side.

### What we did

- **All secrets loaded from environment variables:**
  - `SALESFORCE_CLIENT_ID` — OAuth Connected App consumer key
  - `SALESFORCE_CLIENT_SECRET` — OAuth Connected App consumer secret
  - `ANTHROPIC_API_KEY` — Anthropic API key for AI features
  - `APP_BASE_URL` — (optional) base URL for OAuth callback

- **No secrets in source code** — Grep confirms zero hardcoded API keys, passwords, or tokens in any `.py` or `.js` file.

- **No secrets in frontend** — The `GET /orgs` endpoint returns only `org_id`, `username`, and `instance_url`. Access tokens and refresh tokens are never sent to the browser.

- **`.gitignore` exclusions:**
  ```
  tokens.json
  .env
  ```

- **Token storage** — `tokens.json` stores OAuth access and refresh tokens locally. It is:
  - Excluded from version control via `.gitignore`
  - Only read/written server-side by `auth.py`
  - Never served by the static file handler

- **PKCE (Proof Key for Code Exchange)** — The OAuth flow uses SHA-256 PKCE challenges to prevent authorization code interception attacks.

### Production recommendation

For shared-server deployment, encrypt `tokens.json` at rest using OS-level file encryption or a secrets manager.

---

## 4. Access Control (IDOR Protection)

**Goal:** Ensure every request verifies the logged-in user owns the data being accessed. Prevent insecure direct object reference (IDOR) vulnerabilities by enforcing ownership checks before reading, modifying, or deleting any resource.

### What we did

- **Input validation on all path parameters:**
  - `record_id` — Validated against Salesforce 15/18-character ID regex (`^[A-Za-z0-9]{15,18}$`). Rejects injection attempts.
  - `flow_id` — Validated against Salesforce DeveloperName regex (`^[A-Za-z][A-Za-z0-9_]{0,79}$`). Blocks path traversal.
  - `object_name` — Restricted to the `SUPPORTED_OBJECTS` whitelist (`Account`, `Contact`, `Lead`, `Opportunity`). Arbitrary object access is blocked.

- **CORS restriction** — Cross-Origin Resource Sharing locked to `http://localhost:8000`. External sites cannot make API calls to OrgScan.

- **Org-scoped operations** — All scan, delete, and write operations require `_active_org` to be set (meaning a valid OAuth connection exists). Without it, endpoints return `400 Bad Request`.

- **Salesforce enforces row-level security** — Even if someone crafted a malicious `record_id`, Salesforce itself enforces the connected user's sharing rules, profile permissions, and field-level security. OrgScan cannot access data the authenticated Salesforce user cannot access.

### Architecture note

OrgScan is designed as a single-user local tool — the operator IS the authenticated user. There is no multi-tenant user system. The OAuth token belongs to whoever completed the Salesforce login flow, and all operations run under that user's Salesforce permissions.

### Production recommendation

For multi-user deployment, add session-based authentication (login cookie or JWT) so each browser session is tied to a specific user, and verify session ownership on every API call.

---

## 5. Security Architecture Summary

```
Browser (localhost:8000)
  │
  ├── Static files (HTML/CSS/JS) — no secrets, all data via esc() XSS protection
  │
  ├── API calls (fetch) ──► FastAPI server
  │     │
  │     ├── Rate limiter (per-IP, per-bucket)
  │     ├── Input validation (regex on IDs, names, object whitelist)
  │     ├── Request logging (method, path, status, latency, IP)
  │     │
  │     ├──► Salesforce REST API (OAuth 2.0 + PKCE)
  │     │     └── Tokens from env vars, stored in tokens.json (gitignored)
  │     │
  │     └──► Anthropic API (API key from env var)
  │
  └── CORS: same-origin only
```

---

## 6. Files Involved

| File | Security role |
|------|--------------|
| `main.py` | Rate limiting, input validation, request logging, CORS config |
| `auth.py` | OAuth 2.0 + PKCE flow, token storage, env var secrets |
| `sf_client.py` | DeveloperName validation, auto token refresh, no raw SQL |
| `ai_describer.py` | API key from env var only |
| `.gitignore` | Excludes `tokens.json` and `.env` |
| `static/app.js` | XSS protection via `esc()` on all user data |

---

## 7. What to do before production deployment

1. **Add HTTPS** — Use a reverse proxy (nginx, Caddy) with TLS certificates
2. **Add session auth** — Cookie or JWT-based login if deploying for multiple users
3. **Encrypt token storage** — Encrypt `tokens.json` at rest
4. **Set `APP_BASE_URL`** — Point OAuth callback to your production domain
5. **Restrict `allow_origins`** in CORS to your production domain
6. **Add CSP headers** — Content-Security-Policy to prevent XSS via injected scripts
7. **Monitor logs** — Ship structured logs to a monitoring service for alerting on rate limit violations and errors
