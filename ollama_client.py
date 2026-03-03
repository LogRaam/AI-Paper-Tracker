"""Ollama local LLM client for AI paper suggestions."""

import json
import re
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore


class OllamaNotAvailableError(Exception):
    """Raised when Ollama is not running or not reachable."""
    pass


class OllamaClient:
    """Thin client for the Ollama REST API (http://localhost:11434)."""

    BASE_URL = "http://localhost:11434"

    @classmethod
    def list_models(cls) -> List[str]:
        """Return list of locally available model names.

        Raises OllamaNotAvailableError if Ollama is not running.
        """
        if requests is None:
            raise OllamaNotAvailableError(
                "The 'requests' library is not installed. "
                "Run: pip install requests"
            )
        try:
            resp = requests.get(f"{cls.BASE_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return models
        except requests.exceptions.ConnectionError:
            raise OllamaNotAvailableError(
                f"Cannot connect to Ollama at {cls.BASE_URL}. "
                "Make sure Ollama is running."
            )
        except requests.exceptions.Timeout:
            raise OllamaNotAvailableError(
                f"Ollama at {cls.BASE_URL} did not respond in time."
            )
        except Exception as e:
            raise OllamaNotAvailableError(f"Unexpected error: {e}")

    @classmethod
    def generate(cls, model: str, prompt: str, timeout: int = 120) -> str:
        """Send a prompt to Ollama and return the generated text.

        Args:
            model: Model name (e.g. "qwen3:8b")
            prompt: The full prompt string
            timeout: HTTP timeout in seconds

        Returns:
            The raw text response from the model.

        Raises:
            OllamaNotAvailableError: If Ollama is unreachable.
            Exception: On HTTP errors or timeouts.
        """
        if requests is None:
            raise OllamaNotAvailableError(
                "The 'requests' library is not installed. "
                "Run: pip install requests"
            )
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,   # Low temperature for consistent JSON output
                "num_predict": 1024,
            }
        }
        try:
            resp = requests.post(
                f"{cls.BASE_URL}/api/generate",
                json=payload,
                timeout=timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except requests.exceptions.ConnectionError:
            raise OllamaNotAvailableError(
                f"Cannot connect to Ollama at {cls.BASE_URL}."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Ollama request timed out after {timeout}s. "
                "Try a smaller batch or a faster model."
            )

    @staticmethod
    def extract_json(text: str) -> List[dict]:
        """Robustly extract a JSON array from model output.

        The model sometimes adds preamble text before the JSON array.
        This method finds the first '[' and last ']' and parses between them.

        Returns:
            Parsed list of dicts, or [] if parsing fails.
        """
        try:
            # Find outermost JSON array
            start = text.find('[')
            end = text.rfind(']')
            if start == -1 or end == -1 or end <= start:
                return []
            json_str = text[start:end + 1]
            parsed = json.loads(json_str)
            if not isinstance(parsed, list):
                return []
            # Keep only items that have both "id" and "reason"
            valid = [
                item for item in parsed
                if isinstance(item, dict)
                and "id" in item
                and "reason" in item
            ]
            return valid
        except (json.JSONDecodeError, ValueError):
            return []
