import json
import subprocess
from unittest.mock import patch, MagicMock

from claude_switcher.keychain import read_credentials, write_credentials, delete_credentials

FAKE_CREDS = json.dumps({"accessToken": "sk-ant-oat01-xxx", "refreshToken": "sk-ant-ort01-xxx"})


class TestReadCredentials:
    @patch("claude_switcher.keychain.subprocess.run")
    def test_read_existing_entry(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=FAKE_CREDS)
        result = read_credentials("claude-switcher:emile@gmail.com")
        assert result == FAKE_CREDS
        mock_run.assert_called_once_with(
            ["security", "find-generic-password", "-s", "claude-switcher:emile@gmail.com", "-w"],
            capture_output=True,
            text=True,
        )

    @patch("claude_switcher.keychain.subprocess.run")
    def test_read_missing_entry_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=44, stdout="", stderr="not found")
        result = read_credentials("claude-switcher:missing@test.com")
        assert result is None


class TestWriteCredentials:
    @patch("claude_switcher.keychain.subprocess.run")
    def test_write_credentials(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        write_credentials("claude-switcher:emile@gmail.com", "emilejouannet", FAKE_CREDS)
        mock_run.assert_called_once_with(
            [
                "security", "add-generic-password",
                "-U",
                "-s", "claude-switcher:emile@gmail.com",
                "-a", "emilejouannet",
                "-w", FAKE_CREDS,
            ],
            capture_output=True,
            text=True,
        )

    @patch("claude_switcher.keychain.subprocess.run")
    def test_write_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="permission denied")
        try:
            write_credentials("claude-switcher:test@test.com", "testuser", FAKE_CREDS)
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "Keychain write failed" in str(e)


class TestDeleteCredentials:
    @patch("claude_switcher.keychain.subprocess.run")
    def test_delete_existing(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = delete_credentials("claude-switcher:emile@gmail.com")
        assert result is True

    @patch("claude_switcher.keychain.subprocess.run")
    def test_delete_missing_returns_false(self, mock_run):
        mock_run.return_value = MagicMock(returncode=44)
        result = delete_credentials("claude-switcher:missing@test.com")
        assert result is False


class TestReadAccountAttribute:
    @patch("claude_switcher.keychain.subprocess.run")
    def test_read_account_attribute(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr='    "acct"<blob>="emilejouannet"\n',
        )
        from claude_switcher.keychain import read_account_attribute
        result = read_account_attribute("Claude Code-credentials")
        assert result == "emilejouannet"
