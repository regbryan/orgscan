import base64
import hashlib
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).parent
TOKENS_FILE = BASE_DIR / "tokens.json"
SF_LOGIN_URL = "https://login.salesforce.com"

_pending_verifiers: dict[str, str] = {}


def _generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge)."""
    code_verifier = secrets.token_urlsafe(43)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


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
    code_verifier, code_challenge = _generate_pkce_pair()
    _pending_verifiers[state] = code_verifier
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "scope": "api refresh_token",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{SF_LOGIN_URL}/services/oauth2/authorize?{urlencode(params)}"


def exchange_code(code: str, state: str = "") -> dict:
    """Exchange auth code for access + refresh tokens. Returns token dict.

    Raises ValueError if the state parameter is missing or doesn't match
    a pending PKCE verifier (prevents CSRF and ensures PKCE is enforced).
    """
    if not state:
        raise ValueError("Missing OAuth state parameter. Please try connecting again.")
    code_verifier = _pending_verifiers.pop(state, None)
    if not code_verifier:
        raise ValueError("Invalid or expired OAuth state. Please try connecting again.")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "redirect_uri": _redirect_uri(),
        "code_verifier": code_verifier,
    }
    resp = requests.post(f"{SF_LOGIN_URL}/services/oauth2/token", data=data)
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
    # Restrict file permissions to owner-only (read/write)
    try:
        os.chmod(TOKENS_FILE, 0o600)
    except OSError:
        pass  # Windows doesn't support chmod the same way — acceptable


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
