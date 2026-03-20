import json
from pathlib import Path

from codex_switcher.config import (
    AccountInfo,
    load_accounts,
    save_accounts,
    add_account,
    remove_account,
    get_active_account,
    set_active_account,
)


class TestAccountInfo:
    def test_create_account(self):
        acc = AccountInfo(
            email="test@test.com",
            subscription_type="pro",
            org_name="Test Org",
            active=True,
            keychain_account="testuser",
        )
        assert acc.email == "test@test.com"
        assert acc.active is True


class TestLoadSave:
    def test_load_empty_returns_empty_list(self, tmp_path):
        result = load_accounts(tmp_path / "accounts.json")
        assert result == []

    def test_load_corrupted_json_returns_empty_list(self, tmp_path):
        path = tmp_path / "accounts.json"
        path.write_text("not valid json{{{")
        result = load_accounts(path)
        assert result == []

    def test_load_missing_accounts_key_returns_empty_list(self, tmp_path):
        path = tmp_path / "accounts.json"
        path.write_text('{"other": []}')
        result = load_accounts(path)
        assert result == []

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "accounts.json"
        accounts = [
            AccountInfo("a@test.com", "pro", "Org A", True, "usera"),
            AccountInfo("b@test.com", "pro", "Org B", False, "userb"),
        ]
        save_accounts(accounts, path)
        loaded = load_accounts(path)
        assert len(loaded) == 2
        assert loaded[0].email == "a@test.com"
        assert loaded[1].active is False


class TestAccountOperations:
    def test_add_account(self, tmp_path):
        path = tmp_path / "accounts.json"
        acc = AccountInfo("a@test.com", "pro", "Org", False, "usera")
        add_account(acc, path)
        loaded = load_accounts(path)
        assert len(loaded) == 1

    def test_add_existing_updates(self, tmp_path):
        path = tmp_path / "accounts.json"
        acc1 = AccountInfo("a@test.com", "pro", "Org", True, "usera")
        acc2 = AccountInfo("a@test.com", "team", "New Org", True, "usera")
        add_account(acc1, path)
        add_account(acc2, path)
        loaded = load_accounts(path)
        assert len(loaded) == 1
        assert loaded[0].subscription_type == "team"

    def test_remove_account(self, tmp_path):
        path = tmp_path / "accounts.json"
        add_account(AccountInfo("a@test.com", "pro", "Org", True, "u"), path)
        add_account(AccountInfo("b@test.com", "pro", "Org", False, "u"), path)
        remove_account("a@test.com", path)
        loaded = load_accounts(path)
        assert len(loaded) == 1
        assert loaded[0].email == "b@test.com"

    def test_get_active_account(self, tmp_path):
        path = tmp_path / "accounts.json"
        add_account(AccountInfo("a@test.com", "pro", "Org", True, "u"), path)
        add_account(AccountInfo("b@test.com", "pro", "Org", False, "u"), path)
        active = get_active_account(path)
        assert active is not None
        assert active.email == "a@test.com"

    def test_set_active_account(self, tmp_path):
        path = tmp_path / "accounts.json"
        add_account(AccountInfo("a@test.com", "pro", "Org", True, "u"), path)
        add_account(AccountInfo("b@test.com", "pro", "Org", False, "u"), path)
        set_active_account("b@test.com", path)
        loaded = load_accounts(path)
        assert loaded[0].active is False
        assert loaded[1].active is True
