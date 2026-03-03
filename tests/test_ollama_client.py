"""Tests for ollama_client.py — mocked HTTP calls, no real Ollama needed."""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ollama_client import OllamaClient, OllamaNotAvailableError


# ============================================================
# OllamaClient.list_models
# ============================================================

class TestListModels:
    def test_returns_model_names(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [{"name": "qwen3:8b"}, {"name": "mistral"}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch('ollama_client.requests') as mock_requests:
            mock_requests.get.return_value = mock_resp
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            result = OllamaClient.list_models()

        assert result == ["qwen3:8b", "mistral"]

    def test_empty_models_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": []}
        mock_resp.raise_for_status = MagicMock()

        with patch('ollama_client.requests') as mock_requests:
            mock_requests.get.return_value = mock_resp
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            result = OllamaClient.list_models()

        assert result == []

    def test_raises_when_offline(self):
        with patch('ollama_client.requests') as mock_requests:
            mock_requests.get.side_effect = ConnectionError("refused")
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            with pytest.raises(OllamaNotAvailableError):
                OllamaClient.list_models()

    def test_raises_on_timeout(self):
        with patch('ollama_client.requests') as mock_requests:
            mock_requests.get.side_effect = TimeoutError("timed out")
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            with pytest.raises(OllamaNotAvailableError):
                OllamaClient.list_models()

    def test_raises_when_requests_none(self):
        import ollama_client as oc
        original = oc.requests
        try:
            oc.requests = None
            with pytest.raises(OllamaNotAvailableError, match="requests"):
                OllamaClient.list_models()
        finally:
            oc.requests = original


# ============================================================
# OllamaClient.generate
# ============================================================

class TestGenerate:
    def test_returns_response_text(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Some generated text"}
        mock_resp.raise_for_status = MagicMock()

        with patch('ollama_client.requests') as mock_requests:
            mock_requests.post.return_value = mock_resp
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            result = OllamaClient.generate("qwen3:8b", "Test prompt")

        assert result == "Some generated text"

    def test_empty_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": ""}
        mock_resp.raise_for_status = MagicMock()

        with patch('ollama_client.requests') as mock_requests:
            mock_requests.post.return_value = mock_resp
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            result = OllamaClient.generate("qwen3:8b", "prompt")

        assert result == ""

    def test_raises_on_connection_error(self):
        with patch('ollama_client.requests') as mock_requests:
            mock_requests.post.side_effect = ConnectionError("refused")
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            with pytest.raises(OllamaNotAvailableError):
                OllamaClient.generate("qwen3:8b", "prompt")

    def test_raises_on_timeout(self):
        with patch('ollama_client.requests') as mock_requests:
            mock_requests.post.side_effect = TimeoutError("timed out")
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            with pytest.raises(TimeoutError):
                OllamaClient.generate("qwen3:8b", "prompt")

    def test_sends_correct_model(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "ok"}
        mock_resp.raise_for_status = MagicMock()

        with patch('ollama_client.requests') as mock_requests:
            mock_requests.post.return_value = mock_resp
            mock_requests.exceptions.ConnectionError = ConnectionError
            mock_requests.exceptions.Timeout = TimeoutError

            OllamaClient.generate("qwen3:8b", "test prompt", timeout=60)

            call_kwargs = mock_requests.post.call_args
            payload = call_kwargs[1]['json']
            assert payload['model'] == "qwen3:8b"
            assert payload['stream'] is False
            assert payload['prompt'] == "test prompt"

    def test_raises_when_requests_none(self):
        import ollama_client as oc
        original = oc.requests
        try:
            oc.requests = None
            with pytest.raises(OllamaNotAvailableError, match="requests"):
                OllamaClient.generate("qwen3:8b", "prompt")
        finally:
            oc.requests = original


# ============================================================
# OllamaClient.extract_json
# ============================================================

class TestExtractJson:
    def test_clean_json_array(self):
        text = '[{"id": "2501.00001", "reason": "Relevant because..."}]'
        result = OllamaClient.extract_json(text)
        assert len(result) == 1
        assert result[0]['id'] == '2501.00001'
        assert result[0]['reason'] == 'Relevant because...'

    def test_json_with_preamble_text(self):
        text = (
            "Sure! Here are the relevant papers:\n"
            '[{"id": "2501.00001", "reason": "Good match"}]\n'
            "Hope this helps!"
        )
        result = OllamaClient.extract_json(text)
        assert len(result) == 1
        assert result[0]['id'] == '2501.00001'

    def test_multiple_results(self):
        items = [
            {"id": "2501.00001", "reason": "Reason A"},
            {"id": "2501.00002", "reason": "Reason B"},
            {"id": "2501.00003", "reason": "Reason C"},
        ]
        text = json.dumps(items)
        result = OllamaClient.extract_json(text)
        assert len(result) == 3

    def test_empty_array(self):
        result = OllamaClient.extract_json("[]")
        assert result == []

    def test_empty_array_with_preamble(self):
        result = OllamaClient.extract_json("No relevant papers found.\n[]")
        assert result == []

    def test_invalid_json_returns_empty(self):
        result = OllamaClient.extract_json("This is not JSON at all")
        assert result == []

    def test_broken_json_returns_empty(self):
        result = OllamaClient.extract_json('[{"id": "abc", "reason": broken}]')
        assert result == []

    def test_missing_id_field_excluded(self):
        text = '[{"reason": "Missing ID field"}]'
        result = OllamaClient.extract_json(text)
        assert result == []

    def test_missing_reason_field_excluded(self):
        text = '[{"id": "2501.00001"}]'
        result = OllamaClient.extract_json(text)
        assert result == []

    def test_mixed_valid_and_invalid_items(self):
        text = (
            '[{"id": "2501.00001", "reason": "Valid"}, '
            '{"reason": "No id"}, '
            '{"id": "2501.00003", "reason": "Also valid"}]'
        )
        result = OllamaClient.extract_json(text)
        assert len(result) == 2
        ids = [r['id'] for r in result]
        assert '2501.00001' in ids
        assert '2501.00003' in ids

    def test_empty_string_returns_empty(self):
        result = OllamaClient.extract_json("")
        assert result == []

    def test_object_not_array_returns_empty(self):
        result = OllamaClient.extract_json('{"id": "abc", "reason": "x"}')
        assert result == []
