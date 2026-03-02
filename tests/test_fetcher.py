"""Tests for fetcher.py — pure logic functions and retry_request."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fetcher import is_meta_analysis, get_category_display, retry_request


# ============================================================
# is_meta_analysis
# ============================================================

class TestIsMetaAnalysis:
    def test_title_with_survey(self):
        assert is_meta_analysis("A Comprehensive Survey of Deep Learning", "") is True

    def test_abstract_with_survey(self):
        assert is_meta_analysis("Some Title", "This is a survey of recent methods.") is True

    def test_systematic_review(self):
        assert is_meta_analysis("Systematic Review of NLP Models", "") is True

    def test_meta_analysis_keyword(self):
        assert is_meta_analysis("A meta-analysis of training methods", "") is True

    def test_meta_analysis_without_hyphen(self):
        assert is_meta_analysis("A meta analysis of training methods", "") is True

    def test_state_of_the_art(self):
        assert is_meta_analysis("State of the Art in Computer Vision", "") is True

    def test_state_of_the_art_hyphenated(self):
        assert is_meta_analysis("State-of-the-art methods for NLP", "") is True

    def test_overview_of(self):
        assert is_meta_analysis("An Overview of Transformer Architectures", "") is True

    def test_review_of(self):
        assert is_meta_analysis("A Review of Attention Mechanisms", "") is True

    def test_comprehensive_survey(self):
        assert is_meta_analysis("", "This comprehensive survey covers recent advances.") is True

    def test_systematic_literature(self):
        assert is_meta_analysis("", "A systematic literature review on reinforcement learning.") is True

    def test_no_match(self):
        assert is_meta_analysis("Improving Transformer Training Speed", "We present a new optimization technique.") is False

    def test_case_insensitive(self):
        assert is_meta_analysis("A COMPREHENSIVE SURVEY", "") is True

    def test_mixed_case(self):
        assert is_meta_analysis("Systematic REVIEW of Methods", "") is True

    def test_empty_title_and_abstract(self):
        assert is_meta_analysis("", "") is False

    def test_keyword_in_abstract_not_title(self):
        assert is_meta_analysis("Fast Training", "We provide a survey of optimization.") is True

    def test_partial_keyword_no_match(self):
        # "view" alone should not match "review of"
        assert is_meta_analysis("A new view on data", "Simple approach.") is False


# ============================================================
# get_category_display
# ============================================================

class TestGetCategoryDisplay:
    def test_single_known_category(self):
        assert get_category_display("cs.LG") == "MachineLearning"

    def test_multiple_known_categories(self):
        result = get_category_display("cs.LG cs.CV")
        assert result == "MachineLearning, ComputerVision"

    def test_unknown_category_passthrough(self):
        assert get_category_display("cs.XX") == "cs.XX"

    def test_mix_known_and_unknown(self):
        result = get_category_display("cs.LG cs.XX")
        assert result == "MachineLearning, cs.XX"

    def test_empty_string(self):
        assert get_category_display("") == ""

    def test_all_9_categories(self):
        all_cats = "cs.LG cs.CL cs.CV cs.NE cs.AI cs.RO stat.ML cs.CY cs.SE"
        result = get_category_display(all_cats)
        assert "MachineLearning" in result
        assert "NLP" in result
        assert "ComputerVision" in result
        assert "Robotics" in result
        assert "SoftwareEngineering" in result


# ============================================================
# retry_request
# ============================================================

class TestRetryRequest:
    def test_success_on_first_try(self):
        func = MagicMock(return_value="ok")
        result = retry_request(func, max_retries=3, initial_delay=0)
        assert result == "ok"
        assert func.call_count == 1

    @patch('fetcher.time.sleep')
    def test_success_on_second_try(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("fail"), "ok"])
        result = retry_request(func, max_retries=3, initial_delay=1)
        assert result == "ok"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch('fetcher.time.sleep')
    def test_success_on_third_try(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
        result = retry_request(func, max_retries=3, initial_delay=1)
        assert result == "ok"
        assert func.call_count == 3

    @patch('fetcher.time.sleep')
    def test_all_retries_fail_raises(self, mock_sleep):
        func = MagicMock(side_effect=Exception("persistent failure"))
        with pytest.raises(Exception, match="persistent failure"):
            retry_request(func, max_retries=3, initial_delay=1)
        assert func.call_count == 3

    @patch('fetcher.time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
        retry_request(func, max_retries=3, initial_delay=5)
        # Delays: 5 * 2^0 = 5, 5 * 2^1 = 10
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [5, 10]

    @patch('fetcher.time.sleep')
    def test_log_callback_called_on_retry(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("oops"), "ok"])
        log_cb = MagicMock()
        retry_request(func, max_retries=3, initial_delay=1, log_callback=log_cb)
        log_cb.assert_called_once()
        msg = log_cb.call_args[0][0]
        assert "Retry 1/3" in msg
        assert "oops" in msg

    @patch('fetcher.time.sleep')
    @patch('builtins.print')
    def test_print_fallback_when_no_callback(self, mock_print, mock_sleep):
        func = MagicMock(side_effect=[Exception("oops"), "ok"])
        retry_request(func, max_retries=3, initial_delay=1, log_callback=None)
        mock_print.assert_called_once()
        msg = mock_print.call_args[0][0]
        assert "Retry 1/3" in msg

    def test_max_retries_one(self):
        func = MagicMock(side_effect=Exception("fail"))
        with pytest.raises(Exception, match="fail"):
            retry_request(func, max_retries=1, initial_delay=0)
        assert func.call_count == 1

    @patch('fetcher.time.sleep')
    def test_preserves_return_type(self, mock_sleep):
        func = MagicMock(return_value={"key": "value"})
        result = retry_request(func, max_retries=1)
        assert result == {"key": "value"}
