import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
TOKENS_FILE = BASE_DIR / "tokens.json"
SF_LOGIN_URL = "https://login.salesforce.com"


def _client_id() -> str:
    return os.environ["SALESFORCE_CLIENT_ID"]


def _client_secret() -> str:
    return os.environ["SALESFORCE_CLIENT_SECRET"]


def _redirect_uri() -> str:
    base = os.environ.get("APP_BASE_URL", "http://localhost:8000")
    return f"{base}/orgs/callback"


def get_auth_url(state: str | None = None) -> str:
    if state is None:
        state = secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "scope": "api refresh_token",
        "state": state,
    }
    return f"{SF_LOGIN_URL}/services/oauth2/authorize?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange auth code for access + refresh tokens. Returns token dict."""
    resp = requests.post(
        f"{SF_LOGIN_URL}/services/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri(),
        },
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(org_id: str) -> dict:
    """Refresh the access token for org_id. Updates tokens.json and returns updated org dict."""
    tokens = load_tokens()
    org = tokens.get(org_id)
    if not org:
        raise ValueError(f"Org {org_id} not found")
    resp = requests.post(
        f"{SF_LOGIN_URL}/services/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": org["refresh_token"],
            "client_id": _client_id(),
            "client_secret": _client_secret(),
        },
    )
    resp.raise_for_status()
    data = resp.json()
    org["access_token"] = data["access_token"]
    tokens[org_id] = org
    save_tokens(tokens)
    return org


def load_tokens() -> dict:
    if not TOKENS_FILE.exists():
        return {}
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def save_tokens(tokens: dict) -> None:
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def get_org(org_id: str) -> dict | None:
    return load_tokens().get(org_id)


def remove_org(org_id: str) -> None:
    tokens = load_tokens()
    tokens.pop(org_id, None)
    save_tokens(tokens)


def list_orgs() -> list[dict]:
    tokens = load_tokens()
    return [
        {
            "org_id": org_id,
            "username": data.get("username", ""),
            "instance_url": data.get("instance_url", ""),
        }
        for org_id, data in tokens.items()
    ]


def store_token_response(token_data: dict) -> str:
    """Store token response from Salesforce and return the org_id."""
    user_id_url = token_data.get("id", "")
    org_id = user_id_url.split("/")[-1] if "/" in user_id_url else secrets.token_hex(8)

    tokens = load_tokens()
    tokens[org_id] = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "instance_url": token_data["instance_url"],
        "username": token_data.get("username", ""),
        "id_url": user_id_url,
    }
    save_tokens(tokens)
    return org_id
