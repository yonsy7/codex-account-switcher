"""Account list persistence in ~/.config/codex-switcher/accounts.json."""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "codex-switcher" / "accounts.json"


@dataclass
class AccountInfo:
    email: str
    subscription_type: str
    org_name: str
    active: bool
    keychain_account: str
    account_id: str = ""


def load_accounts(path: Path = DEFAULT_CONFIG_PATH) -> list[AccountInfo]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return [
            AccountInfo(**{k: v for k, v in acc.items() if k in AccountInfo.__dataclass_fields__})
            for acc in data["accounts"]
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def save_accounts(accounts: list[AccountInfo], path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = {"accounts": [asdict(acc) for acc in accounts]}
    path.write_text(json.dumps(data, indent=2))
    os.chmod(path, 0o600)


def add_account(account: AccountInfo, path: Path = DEFAULT_CONFIG_PATH) -> None:
    accounts = load_accounts(path)
    accounts = [a for a in accounts if a.email != account.email]
    accounts.append(account)
    save_accounts(accounts, path)


def remove_account(email: str, path: Path = DEFAULT_CONFIG_PATH) -> None:
    accounts = load_accounts(path)
    accounts = [a for a in accounts if a.email != email]
    save_accounts(accounts, path)


def get_active_account(path: Path = DEFAULT_CONFIG_PATH) -> AccountInfo | None:
    for acc in load_accounts(path):
        if acc.active:
            return acc
    return None


def set_active_account(email: str, path: Path = DEFAULT_CONFIG_PATH) -> None:
    accounts = load_accounts(path)
    for acc in accounts:
        acc.active = acc.email == email
    save_accounts(accounts, path)
