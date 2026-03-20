"""Business logic for Codex account management."""

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path

from codex_switcher import keychain
from codex_switcher.config import (
    AccountInfo,
    add_account,
    get_active_account,
    load_accounts,
    remove_account,
    set_active_account,
    DEFAULT_CONFIG_PATH,
)

CODEX_AUTH_FILE = Path.home() / ".codex" / "auth.json"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str) -> str:
    if not _EMAIL_RE.match(email) or len(email) > 254:
        raise RuntimeError(f"Invalid email format: {email}")
    return email


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        raw = base64.urlsafe_b64decode(payload.encode())
        return json.loads(raw)
    except Exception:
        return {}


def _read_auth_blob() -> str | None:
    try:
        return CODEX_AUTH_FILE.read_text()
    except OSError:
        return None


def _write_auth_blob(auth_blob: str) -> None:
    CODEX_AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    CODEX_AUTH_FILE.write_text(auth_blob)
    CODEX_AUTH_FILE.chmod(0o600)


def _extract_account_info(auth_blob: str) -> tuple[str, str, str, str]:
    """Return (email, subscription_type, org_name, account_id)."""
    data = json.loads(auth_blob)

    jwt_payload = _decode_jwt_payload(data.get("tokens", {}).get("id_token", ""))
    auth_claim = jwt_payload.get("https://api.openai.com/auth", {}) or {}

    email = (
        data.get("email")
        or jwt_payload.get("email")
        or "unknown@unknown"
    )
    subscription_type = (
        auth_claim.get("chatgpt_plan_type")
        or data.get("plan_type")
        or "unknown"
    )

    org_name = ""
    orgs = auth_claim.get("organizations")
    if isinstance(orgs, list) and orgs:
        org_name = orgs[0].get("title", "") or ""

    account_id = (
        data.get("tokens", {}).get("account_id")
        or auth_claim.get("chatgpt_account_id")
        or ""
    )

    _validate_email(email)
    return email, subscription_type, org_name, account_id


def _find_codex() -> str | None:
    found = shutil.which("codex")
    if found:
        return found

    for d in [Path.home() / ".local" / "bin", Path("/usr/local/bin"), Path("/opt/homebrew/bin")]:
        candidate = d / "codex"
        if candidate.is_file():
            return str(candidate)
    return None


def _codex_cmd() -> str:
    return _find_codex() or "codex"


def check_codex_cli() -> bool:
    return _find_codex() is not None


def run_auth_logout() -> None:
    subprocess.run([_codex_cmd(), "logout"], capture_output=True, text=True)


def run_auth_login() -> bool:
    # Interactive login flow (browser/device auth)
    result = subprocess.run([_codex_cmd(), "login"])
    return result.returncode == 0


def import_current_account(config_path: Path = DEFAULT_CONFIG_PATH) -> AccountInfo | None:
    auth_blob = _read_auth_blob()
    if not auth_blob:
        return None

    try:
        email, sub_type, org_name, account_id = _extract_account_info(auth_blob)
    except Exception:
        return None

    keychain.write_credentials(f"codex-switcher:{email}", email, auth_blob)

    account = AccountInfo(
        email=email,
        subscription_type=sub_type,
        org_name=org_name,
        active=True,
        keychain_account=email,
        account_id=account_id,
    )
    add_account(account, config_path)
    set_active_account(email, config_path)
    return account


def switch_account(target_email: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    active = get_active_account(config_path)

    # Backup current active auth blob
    if active:
        current_auth = _read_auth_blob()
        if current_auth:
            keychain.write_credentials(f"codex-switcher:{active.email}", active.keychain_account, current_auth)

    _validate_email(target_email)
    target_auth = keychain.read_credentials(f"codex-switcher:{target_email}")
    if not target_auth:
        raise RuntimeError(f"Credentials not found in Keychain for {target_email}")

    _write_auth_blob(target_auth)

    # Refresh metadata from restored auth blob
    try:
        email, sub_type, org_name, account_id = _extract_account_info(target_auth)
        add_account(
            AccountInfo(
                email=email,
                subscription_type=sub_type,
                org_name=org_name,
                active=True,
                keychain_account=email,
                account_id=account_id,
            ),
            config_path,
        )
    except Exception:
        pass

    set_active_account(target_email, config_path)


def add_new_account(config_path: Path = DEFAULT_CONFIG_PATH) -> AccountInfo | None:
    active = get_active_account(config_path)
    if active:
        current_auth = _read_auth_blob()
        if current_auth:
            keychain.write_credentials(f"codex-switcher:{active.email}", active.keychain_account, current_auth)

    run_auth_logout()

    if not run_auth_login():
        if active:
            prev_auth = keychain.read_credentials(f"codex-switcher:{active.email}")
            if prev_auth:
                _write_auth_blob(prev_auth)
        return None

    try:
        return import_current_account(config_path)
    except Exception:
        if active:
            prev_auth = keychain.read_credentials(f"codex-switcher:{active.email}")
            if prev_auth:
                _write_auth_blob(prev_auth)
        return None


def remove_saved_account(email: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    keychain.delete_credentials(f"codex-switcher:{email}")
    remove_account(email, config_path)
