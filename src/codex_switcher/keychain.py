"""Wrapper around macOS `security` CLI for Keychain credential management."""

import re
import subprocess


def read_credentials(service: str) -> str | None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() if result.stdout.strip() else None


def write_credentials(service: str, account: str, password: str) -> None:
    while True:
        r = subprocess.run(
            ["security", "delete-generic-password", "-s", service],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            break

    result = subprocess.run(
        [
            "security",
            "add-generic-password",
            "-s",
            service,
            "-a",
            account,
            "-w",
            password,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Keychain write failed. Check macOS Keychain access permissions.")


def delete_credentials(service: str) -> bool:
    result = subprocess.run(
        ["security", "delete-generic-password", "-s", service],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def read_account_attribute(service: str) -> str | None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    match = re.search(r'"acct"<blob>="([^"]*)"', result.stdout)
    return match.group(1) if match else None
