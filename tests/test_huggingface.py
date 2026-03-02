"""Tests for huggingface_fetcher.py — retry_request (HF version)."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from huggingface_fetcher import retry_request


# ============================================================
# retry_request (Hugging Face version)
# Note: This is a duplicate of fetcher.retry_request.
# Tests verify the HF copy works independently.
# ============================================================

class TestHFRetryRequest:
    def test_success_on_first_try(self):
        func = MagicMock(return_value="ok")
        result = retry_request(func, max_retries=3, initial_delay=0)
        assert result == "ok"
        assert func.call_count == 1

    @patch('huggingface_fetcher.time.sleep')
    def test_success_after_one_failure(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("fail"), "ok"])
        result = retry_request(func, max_retries=3, initial_delay=2)
        assert result == "ok"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(2)

    @patch('huggingface_fetcher.time.sleep')
    def test_all_retries_fail(self, mock_sleep):
        func = MagicMock(side_effect=Exception("persistent"))
        with pytest.raises(Exception, match="persistent"):
            retry_request(func, max_retries=3, initial_delay=1)
        assert func.call_count == 3

    @patch('huggingface_fetcher.time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
        retry_request(func, max_retries=3, initial_delay=5)
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [5, 10]

    @patch('huggingface_fetcher.time.sleep')
    def test_log_callback_used(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("err"), "ok"])
        log_cb = MagicMock()
        retry_request(func, max_retries=3, initial_delay=1, log_callback=log_cb)
        log_cb.assert_called_once()
        assert "Retry 1/3" in log_cb.call_args[0][0]

    @patch('huggingface_fetcher.time.sleep')
    @patch('builtins.print')
    def test_print_fallback(self, mock_print, mock_sleep):
        func = MagicMock(side_effect=[Exception("err"), "ok"])
        retry_request(func, max_retries=3, initial_delay=1, log_callback=None)
        mock_print.assert_called_once()

    def test_single_retry_fails(self):
        func = MagicMock(side_effect=ValueError("bad"))
        with pytest.raises(ValueError, match="bad"):
            retry_request(func, max_retries=1, initial_delay=0)
        assert func.call_count == 1

    @patch('huggingface_fetcher.time.sleep')
    def test_returns_correct_type(self, mock_sleep):
        func = MagicMock(return_value=[1, 2, 3])
        result = retry_request(func, max_retries=2, initial_delay=0)
        assert result == [1, 2, 3]
