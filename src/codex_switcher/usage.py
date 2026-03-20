"""Fetch Codex usage stats from ChatGPT backend usage endpoint."""

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from codex_switcher import keychain

USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


def _extract_tokens(auth_json: str) -> tuple[str | None, str | None]:
    try:
        data = json.loads(auth_json)
        tokens = data.get("tokens", {})
        return tokens.get("access_token"), tokens.get("account_id")
    except (json.JSONDecodeError, AttributeError):
        return None, None


def fetch_usage_from_auth_blob(auth_blob: str) -> dict | None:
    access_token, account_id = _extract_tokens(auth_blob)
    if not access_token:
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "CodexBar",
        "Accept": "application/json",
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id

    req = urllib.request.Request(USAGE_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def fetch_usage_for_account(email: str) -> dict | None:
    auth_blob = keychain.read_credentials(f"codex-switcher:{email}")
    if not auth_blob:
        return None
    return fetch_usage_from_auth_blob(auth_blob)


def fetch_active_usage() -> dict | None:
    try:
        from codex_switcher.core import CODEX_AUTH_FILE
        auth_blob = CODEX_AUTH_FILE.read_text()
    except OSError:
        return None
    return fetch_usage_from_auth_blob(auth_blob)


def _format_reset_delta_from_epoch(reset_at_seconds: int | None) -> str:
    if not reset_at_seconds:
        return "?"
    try:
        reset_dt = datetime.fromtimestamp(reset_at_seconds, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = int((reset_dt - now).total_seconds())
        if diff <= 0:
            return "now"

        days = diff // 86400
        hours = (diff % 86400) // 3600
        minutes = (diff % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "?"


def format_usage(usage: dict | None) -> str:
    if not usage:
        return "Usage indisponible"

    rate_limit = usage.get("rate_limit") or {}
    primary = rate_limit.get("primary_window") or {}
    secondary = rate_limit.get("secondary_window") or {}

    parts = []
    if "used_percent" in primary:
        label = f"{round((primary.get('limit_window_seconds', 10800) / 3600))}h"
        parts.append(f"{label} {primary['used_percent']:.0f}% ({_format_reset_delta_from_epoch(primary.get('reset_at'))})")
    if "used_percent" in secondary:
        sec_hours = round((secondary.get("limit_window_seconds", 86400) / 3600))
        label = "Week" if sec_hours >= 168 else ("Day" if sec_hours >= 24 else f"{sec_hours}h")
        parts.append(f"{label} {secondary['used_percent']:.0f}% ({_format_reset_delta_from_epoch(secondary.get('reset_at'))})")

    return " | ".join(parts) if parts else "Usage indisponible"
