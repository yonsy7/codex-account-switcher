import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from claude_switcher.core import (
    check_claude_cli,
    get_auth_status,
    run_auth_logout,
    run_auth_login,
    import_current_account,
    switch_account,
    add_new_account,
    remove_saved_account,
)
from claude_switcher.config import AccountInfo


class TestClaudeCLI:
    @patch("claude_switcher.core.shutil.which")
    def test_check_cli_found(self, mock_which):
        mock_which.return_value = "/usr/local/bin/claude"
        assert check_claude_cli() is True

    @patch("claude_switcher.core.shutil.which")
    def test_check_cli_not_found(self, mock_which):
        mock_which.return_value = None
        assert check_claude_cli() is False

    @patch("claude_switcher.core.subprocess.run")
    def test_get_auth_status(self, mock_run):
        status = {"loggedIn": True, "email": "test@test.com", "subscriptionType": "pro", "orgName": "Org"}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(status))
        result = get_auth_status()
        assert result["email"] == "test@test.com"

    @patch("claude_switcher.core.subprocess.run")
    def test_get_auth_status_failure_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = get_auth_status()
        assert result is None


class TestImportCurrentAccount:
    @patch("claude_switcher.core.get_auth_status")
    @patch("claude_switcher.core.keychain")
    def test_import_success(self, mock_kc, mock_status, tmp_path):
        mock_status.return_value = {"email": "test@test.com", "subscriptionType": "pro", "orgName": "Org"}
        mock_kc.read_credentials.return_value = '{"accessToken":"tok"}'
        mock_kc.read_account_attribute.return_value = "testuser"

        config_path = tmp_path / "accounts.json"
        result = import_current_account(config_path)

        assert result is not None
        assert result.email == "test@test.com"
        mock_kc.write_credentials.assert_called_once_with(
            "claude-switcher:test@test.com", "testuser", '{"accessToken":"tok"}'
        )

    @patch("claude_switcher.core.get_auth_status")
    @patch("claude_switcher.core.keychain")
    def test_import_no_credentials(self, mock_kc, mock_status, tmp_path):
        mock_kc.read_credentials.return_value = None
        result = import_current_account(tmp_path / "accounts.json")
        assert result is None


class TestSwitchAccount:
    @patch("claude_switcher.core.keychain")
    def test_switch_saves_current_then_loads_target(self, mock_kc, tmp_path):
        config_path = tmp_path / "accounts.json"
        from claude_switcher.config import add_account, AccountInfo
        add_account(AccountInfo("a@test.com", "pro", "Org A", True, "usera"), config_path)
        add_account(AccountInfo("b@test.com", "pro", "Org B", False, "userb"), config_path)

        mock_kc.read_credentials.side_effect = [
            '{"accessToken":"refreshed-a"}',
            '{"accessToken":"tok-b"}',
        ]

        switch_account("b@test.com", config_path)

        mock_kc.write_credentials.assert_any_call(
            "claude-switcher:a@test.com", "usera", '{"accessToken":"refreshed-a"}'
        )
        mock_kc.write_credentials.assert_any_call(
            "Claude Code-credentials", "userb", '{"accessToken":"tok-b"}'
        )

    @patch("claude_switcher.core.keychain")
    def test_switch_missing_keychain_entry_raises(self, mock_kc, tmp_path):
        config_path = tmp_path / "accounts.json"
        from claude_switcher.config import add_account, AccountInfo
        add_account(AccountInfo("a@test.com", "pro", "Org", True, "u"), config_path)
        add_account(AccountInfo("b@test.com", "pro", "Org", False, "u"), config_path)
        mock_kc.read_credentials.side_effect = ['{"tok":"a"}', None]

        try:
            switch_account("b@test.com", config_path)
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "not found" in str(e).lower()


class TestAddNewAccount:
    @patch("claude_switcher.core.get_auth_status")
    @patch("claude_switcher.core.run_auth_login")
    @patch("claude_switcher.core.run_auth_logout")
    @patch("claude_switcher.core.keychain")
    def test_add_account_full_flow(self, mock_kc, mock_logout, mock_login, mock_status, tmp_path):
        config_path = tmp_path / "accounts.json"
        from claude_switcher.config import add_account, AccountInfo
        add_account(AccountInfo("a@test.com", "pro", "Org A", True, "usera"), config_path)

        mock_kc.read_credentials.side_effect = [
            '{"accessToken":"tok-a"}',
            '{"accessToken":"tok-new"}',
        ]
        mock_kc.read_account_attribute.side_effect = ["newuser"]
        mock_login.return_value = True
        mock_status.return_value = {"email": "new@test.com", "subscriptionType": "pro", "orgName": "New Org"}

        result = add_new_account(config_path)
        assert result is not None
        assert result.email == "new@test.com"
        mock_logout.assert_called_once()
        mock_login.assert_called_once()

    @patch("claude_switcher.core.run_auth_login")
    @patch("claude_switcher.core.run_auth_logout")
    @patch("claude_switcher.core.keychain")
    def test_add_account_login_cancelled(self, mock_kc, mock_logout, mock_login, tmp_path):
        config_path = tmp_path / "accounts.json"
        mock_kc.read_credentials.return_value = None
        mock_login.return_value = False

        result = add_new_account(config_path)
        assert result is None


class TestRemoveSavedAccount:
    @patch("claude_switcher.core.keychain")
    def test_remove_account(self, mock_kc, tmp_path):
        config_path = tmp_path / "accounts.json"
        from claude_switcher.config import add_account, AccountInfo
        add_account(AccountInfo("a@test.com", "pro", "Org", False, "u"), config_path)

        remove_saved_account("a@test.com", config_path)

        mock_kc.delete_credentials.assert_called_once_with("claude-switcher:a@test.com")
        from claude_switcher.config import load_accounts
        assert len(load_accounts(config_path)) == 0
