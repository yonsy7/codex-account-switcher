import json
from unittest.mock import patch, MagicMock

from codex_switcher.core import (
    check_codex_cli,
    import_current_account,
    switch_account,
    add_new_account,
    remove_saved_account,
    _extract_account_info,
)
from codex_switcher.config import AccountInfo, add_account, load_accounts


class TestCodexCLI:
    @patch("codex_switcher.core.shutil.which")
    def test_check_cli_found(self, mock_which):
        mock_which.return_value = "/usr/local/bin/codex"
        assert check_codex_cli() is True

    @patch("codex_switcher.core.Path.is_file", return_value=False)
    @patch("codex_switcher.core.shutil.which", return_value=None)
    def test_check_cli_not_found(self, *_):
        assert check_codex_cli() is False


class TestExtractAccountInfo:
    def _jwt(self, payload: dict) -> str:
        import base64
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{header}.{body}.sig"

    def test_extracts_email_plan_org(self):
        auth_claim = {
            "chatgpt_plan_type": "pro",
            "chatgpt_account_id": "acc-1",
            "organizations": [{"title": "Personal"}],
        }
        payload = {"email": "test@example.com", "https://api.openai.com/auth": auth_claim}
        blob = json.dumps({"tokens": {"id_token": self._jwt(payload)}})

        email, plan, org, account_id = _extract_account_info(blob)
        assert email == "test@example.com"
        assert plan == "pro"
        assert org == "Personal"
        assert account_id == "acc-1"


class TestImportCurrentAccount:
    @patch("codex_switcher.core.keychain")
    @patch("codex_switcher.core._read_auth_blob")
    @patch("codex_switcher.core._extract_account_info")
    def test_import_success(self, mock_extract, mock_read, mock_kc, tmp_path):
        mock_read.return_value = '{"tokens": {"id_token": "x.y.z"}}'
        mock_extract.return_value = ("test@test.com", "pro", "Org", "acc-1")

        config_path = tmp_path / "accounts.json"
        result = import_current_account(config_path)

        assert result is not None
        assert result.email == "test@test.com"
        mock_kc.write_credentials.assert_called_once()

    @patch("codex_switcher.core._read_auth_blob")
    def test_import_none_without_auth_file(self, mock_read, tmp_path):
        mock_read.return_value = None
        assert import_current_account(tmp_path / "accounts.json") is None


class TestSwitchAccount:
    @patch("codex_switcher.core.keychain")
    @patch("codex_switcher.core._write_auth_blob")
    @patch("codex_switcher.core._read_auth_blob")
    @patch("codex_switcher.core._extract_account_info")
    def test_switch_restores_target_auth(self, mock_extract, mock_read_auth, mock_write_auth, mock_kc, tmp_path):
        config_path = tmp_path / "accounts.json"
        add_account(AccountInfo("a@test.com", "pro", "Org A", True, "a@test.com", "acc-a"), config_path)
        add_account(AccountInfo("b@test.com", "pro", "Org B", False, "b@test.com", "acc-b"), config_path)

        mock_read_auth.return_value = '{"tokens": {"id_token": "a"}}'
        mock_kc.read_credentials.return_value = '{"tokens": {"id_token": "b"}}'
        mock_extract.return_value = ("b@test.com", "pro", "Org B", "acc-b")

        switch_account("b@test.com", config_path)

        mock_write_auth.assert_called_once_with('{"tokens": {"id_token": "b"}}')
        active = [a for a in load_accounts(config_path) if a.active][0]
        assert active.email == "b@test.com"


class TestAddAndRemove:
    @patch("codex_switcher.core.run_auth_login", return_value=False)
    @patch("codex_switcher.core.run_auth_logout")
    def test_add_account_cancelled(self, _mock_logout, _mock_login, tmp_path):
        assert add_new_account(tmp_path / "accounts.json") is None

    @patch("codex_switcher.core.keychain")
    def test_remove_account(self, mock_kc, tmp_path):
        config_path = tmp_path / "accounts.json"
        add_account(AccountInfo("a@test.com", "pro", "Org", False, "a@test.com", ""), config_path)
        remove_saved_account("a@test.com", config_path)
        assert len(load_accounts(config_path)) == 0
        mock_kc.delete_credentials.assert_called_once_with("codex-switcher:a@test.com")
