"""Business logic for account management."""

import json
import shutil
import subprocess
from pathlib import Path

from claude_switcher import keychain
from claude_switcher.config import (
    AccountInfo,
    add_account,
    get_active_account,
    load_accounts,
    remove_account,
    set_active_account,
    DEFAULT_CONFIG_PATH,
)

CLAUDE_SERVICE = keychain.CLAUDE_SERVICE


def check_claude_cli() -> bool:
    """Check if the claude CLI is available on PATH."""
    return shutil.which("claude") is not None


def get_auth_status() -> dict | None:
    """Run `claude auth status --json` and return parsed JSON, or None on failure."""
    result = subprocess.run(
        ["claude", "auth", "status", "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def run_auth_logout() -> None:
    """Run `claude auth logout`."""
    subprocess.run(["claude", "auth", "logout"], capture_output=True, text=True)


def run_auth_login() -> bool:
    """Run `claude auth login`. Returns True if successful (exit code 0)."""
    result = subprocess.run(["claude", "auth", "login"])
    return result.returncode == 0


def import_current_account(config_path: Path = DEFAULT_CONFIG_PATH) -> AccountInfo | None:
    """Import the currently logged-in Claude Code account. Returns AccountInfo or None."""
    creds = keychain.read_credentials(CLAUDE_SERVICE)
    if not creds:
        return None

    acct_attr = keychain.read_account_attribute(CLAUDE_SERVICE) or "unknown"

    status = get_auth_status()
    if status and status.get("email"):
        email = status["email"]
        sub_type = status.get("subscriptionType", "unknown")
        org_name = status.get("orgName", "")
    else:
        try:
            email = json.loads(creds).get("email", "unknown@unknown")
        except (json.JSONDecodeError, AttributeError):
            return None
        sub_type = "unknown"
        org_name = ""

    keychain.write_credentials(f"claude-switcher:{email}", acct_attr, creds)

    account = AccountInfo(
        email=email,
        subscription_type=sub_type,
        org_name=org_name,
        active=True,
        keychain_account=acct_attr,
    )
    add_account(account, config_path)
    return account


def switch_account(target_email: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Switch to a different account. Saves current credentials first."""
    active = get_active_account(config_path)

    if active:
        current_creds = keychain.read_credentials(CLAUDE_SERVICE)
        if current_creds:
            keychain.write_credentials(
                f"claude-switcher:{active.email}", active.keychain_account, current_creds
            )

    target_creds = keychain.read_credentials(f"claude-switcher:{target_email}")
    if not target_creds:
        raise RuntimeError(f"Credentials not found in Keychain for {target_email}")

    accounts = load_accounts(config_path)
    target_account = next((a for a in accounts if a.email == target_email), None)
    if not target_account:
        raise RuntimeError(f"Account {target_email} not found in config")

    keychain.write_credentials(CLAUDE_SERVICE, target_account.keychain_account, target_creds)
    set_active_account(target_email, config_path)


def add_new_account(config_path: Path = DEFAULT_CONFIG_PATH) -> AccountInfo | None:
    """Add a new account via claude auth login. Returns AccountInfo or None if cancelled."""
    active = get_active_account(config_path)
    if active:
        current_creds = keychain.read_credentials(CLAUDE_SERVICE)
        if current_creds:
            keychain.write_credentials(
                f"claude-switcher:{active.email}", active.keychain_account, current_creds
            )

    run_auth_logout()

    if not run_auth_login():
        if active:
            prev_creds = keychain.read_credentials(f"claude-switcher:{active.email}")
            if prev_creds:
                keychain.write_credentials(CLAUDE_SERVICE, active.keychain_account, prev_creds)
        return None

    return import_current_account(config_path)


def remove_saved_account(email: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Remove a saved account from config and Keychain."""
    keychain.delete_credentials(f"claude-switcher:{email}")
    remove_account(email, config_path)
