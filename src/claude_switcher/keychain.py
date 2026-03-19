"""Wrapper around macOS `security` CLI for Keychain credential management."""

import re
import subprocess

CLAUDE_SERVICE = "Claude Code-credentials"


def read_credentials(service: str) -> str | None:
    """Read the password blob for a Keychain entry. Returns None if not found."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() if result.stdout.strip() else None


def write_credentials(service: str, account: str, password: str) -> None:
    """Write (or update) a Keychain entry. Raises RuntimeError on failure."""
    result = subprocess.run(
        [
            "security", "add-generic-password",
            "-U",
            "-s", service,
            "-a", account,
            "-w", password,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Keychain write failed: {result.stderr}")


def delete_credentials(service: str) -> bool:
    """Delete a Keychain entry. Returns True if deleted, False if not found."""
    result = subprocess.run(
        ["security", "delete-generic-password", "-s", service],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def read_account_attribute(service: str) -> str | None:
    """Read the account (-a) attribute of a Keychain entry by parsing security output."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    match = re.search(r'"acct"<blob>="([^"]*)"', result.stderr)
    return match.group(1) if match else None
