# Codex Account Switcher

A lightweight macOS menu bar app to switch between multiple Codex (ChatGPT) accounts instantly — and see usage for each account.

## What it does

- One-click account switching for Codex CLI sessions
- Stores per-account auth blobs securely in macOS Keychain
- Restores selected account into `~/.codex/auth.json`
- Shows live usage windows from ChatGPT backend API
  - primary window (often 3h)
  - secondary window (day/week depending on plan)

## How it works

Codex CLI auth state lives in `~/.codex/auth.json`.

This app keeps per-account backups in Keychain entries:
- `codex-switcher:<email>`

When switching accounts:
1. Backup current `~/.codex/auth.json` to active account Keychain entry
2. Read target account auth blob from Keychain
3. Write it to `~/.codex/auth.json`
4. Mark target as active in `~/.config/codex-switcher/accounts.json`

Usage is fetched via:
- `GET https://chatgpt.com/backend-api/wham/usage`
- Headers: `Authorization: Bearer ***` and optional `ChatGPT-Account-Id`

## Requirements

- macOS 12+
- Codex CLI installed (`codex` in PATH)
- At least one successful Codex login (`~/.codex/auth.json` exists)

## Install

```bash
pip install git+https://github.com/yonsy7/codex-account-switcher.git
codex-switcher
```

## Build from source

```bash
git clone https://github.com/yonsy7/codex-account-switcher.git
cd codex-account-switcher
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && pip install py2app pytest
```

Run app:
```bash
codex-switcher
```

Build standalone app:
```bash
bash build_app.sh
```

## Verify switching

After switching in the menu bar:

```bash
codex login status
```

If the restored account differs, Codex requests under that session will use the restored `~/.codex/auth.json` identity.

## Security notes

- Auth blobs are stored in macOS Keychain (not plaintext files)
- Local config stores metadata only (`~/.config/codex-switcher/accounts.json`, mode 0600)
- No `shell=True` subprocess usage

## Current limitation

Codex CLI currently does not expose a rich `login status --json` output with email/plan,
so metadata is extracted from JWT claims in `id_token`.
