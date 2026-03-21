# OrgScan

Salesforce Org Health Assessment tool for consultants. Connects to client orgs via OAuth, runs automated health checks, generates AI flow descriptions via Claude, and exports branded PDF reports.

## Features

- **5 Health Checks:** Inactive licensed users, outdated flow API versions, missing flow descriptions, unused custom fields, excessive permissions (Modify/View All Data), validation rules without descriptions, hard-coded record IDs in flows
- **AI Flow Descriptions:** Claude reads the flow metadata and writes a plain-English description back to Salesforce
- **Dashboard:** Category Tabs UI — browse findings by Users / Flows / Fields / Permissions / Validation
- **PDF Export:** Branded client-ready report with executive summary, findings by category, and AI-generated narrative

## Setup

### 1. Create a Salesforce Connected App

In your Salesforce org (Setup → App Manager → New Connected App):
- Enable OAuth
- Add scope: `api`, `refresh_token`
- Set callback URL to: `http://localhost:8000/orgs/callback`

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
SALESFORCE_CLIENT_ID=your_connected_app_consumer_key
SALESFORCE_CLIENT_SECRET=your_connected_app_consumer_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
APP_BASE_URL=http://localhost:8000
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Customize branding

Edit `report_config.toml`:
```toml
[branding]
consultant_name = "Your Name"
logo_path = "static/logo.png"   # optional
primary_color = "#1e40af"
```

### 5. Start the server

```bash
uvicorn main:app --reload --port 8000
```

Open: http://localhost:8000

## Usage

1. Click **+ Connect Org** → authorize via Salesforce OAuth login window
2. Select the org from the dropdown → click **Run Scan**
3. Browse findings by category in the left sidebar
4. For flows missing descriptions, click **✨ Generate Description** → review → **Write to Org**
5. Click **Export PDF** → enter client name → PDF downloads automatically

## Running Tests

```bash
pytest -v
```

## Architecture

```
main.py              FastAPI app, all routes, in-memory state
auth.py              OAuth flow + token storage (tokens.json)
sf_client.py         Salesforce REST/Tooling API wrapper
ai_describer.py      Claude API — flow descriptions + PDF narrative
report.py            WeasyPrint PDF generator (Jinja2 template)
score.py             Health score calculator (100 - weighted deductions)
checks/
  users.py           Inactive licensed users
  flows.py           API version, descriptions, hard-coded IDs
  fields.py          Unused custom fields
  permissions.py     Excessive permissions (Modify/View All Data)
  validation_rules.py Validation rules missing descriptions
static/              Dashboard SPA (vanilla JS)
templates/           Jinja2 PDF template
```
