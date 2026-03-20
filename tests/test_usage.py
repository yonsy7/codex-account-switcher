"""Tests for usage module."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from codex_switcher.usage import _extract_tokens, _format_reset_delta_from_epoch, format_usage, fetch_usage_for_account


class TestExtractTokens:
    def test_extracts_access_and_account_id(self):
        blob = json.dumps({"tokens": {"access_token": "tok", "account_id": "acc"}})
        access, account_id = _extract_tokens(blob)
        assert access == "tok"
        assert account_id == "acc"

    def test_returns_none_for_invalid_json(self):
        access, account_id = _extract_tokens("not-json")
        assert access is None
        assert account_id is None


class TestFormatResetDelta:
    def test_future_hours(self):
        future = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())
        result = _format_reset_delta_from_epoch(future)
        assert "h" in result or "m" in result

    def test_past_returns_now(self):
        past = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
        assert _format_reset_delta_from_epoch(past) == "now"


class TestFormatUsage:
    def test_formats_primary_secondary(self):
        now = int(datetime.now(timezone.utc).timestamp())
        usage = {
            "rate_limit": {
                "primary_window": {"used_percent": 42.7, "limit_window_seconds": 10800, "reset_at": now + 3600},
                "secondary_window": {"used_percent": 18.3, "limit_window_seconds": 604800, "reset_at": now + 86400},
            }
        }
        out = format_usage(usage)
        assert "3h 43%" in out
        assert "Week 18%" in out

    def test_unavailable(self):
        assert format_usage(None) == "Usage indisponible"


class TestFetchUsageForAccount:
    @patch("codex_switcher.usage.urllib.request.urlopen")
    @patch("codex_switcher.usage.keychain.read_credentials")
    def test_fetches(self, mock_read, mock_urlopen):
        mock_read.return_value = json.dumps({"tokens": {"access_token": "tok", "account_id": "acc"}})
        response_data = json.dumps({"rate_limit": {}}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_usage_for_account("test@test.com")
        assert result == {"rate_limit": {}}

    @patch("codex_switcher.usage.keychain.read_credentials")
    def test_no_creds(self, mock_read):
        mock_read.return_value = None
        assert fetch_usage_for_account("x@test.com") is None
