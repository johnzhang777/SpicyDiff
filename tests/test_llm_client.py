"""Unit tests for the llm_client module (with mocked OpenAI calls)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from spicydiff.llm_client import call_llm
from spicydiff.models import ReviewResult


def _mock_response(content: str) -> MagicMock:
    """Create a mock OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


class TestCallLLM:
    @patch("spicydiff.llm_client.OpenAI")
    def test_valid_json(self, mock_openai_cls):
        payload = {
            "summary": "Code is raw!",
            "score": 25,
            "reviews": [
                {"file_path": "a.py", "line_number": 3, "comment": "Yikes!"}
            ],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
        mock_openai_cls.return_value = mock_client

        result = call_llm("key", "gpt-4o", "sys", "usr")
        assert isinstance(result, ReviewResult)
        assert result.score == 25
        assert len(result.reviews) == 1

    @patch("spicydiff.llm_client.OpenAI")
    def test_strips_markdown_fences(self, mock_openai_cls):
        payload = {"summary": "Nice!", "score": 90, "reviews": []}
        content = f"```json\n{json.dumps(payload)}\n```"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(content)
        mock_openai_cls.return_value = mock_client

        result = call_llm("key", "gpt-4o", "sys", "usr")
        assert result.score == 90

    @patch("spicydiff.llm_client.OpenAI")
    def test_invalid_json_exits(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response("not json at all")
        mock_openai_cls.return_value = mock_client

        with pytest.raises(SystemExit):
            call_llm("key", "gpt-4o", "sys", "usr")

    @patch("spicydiff.llm_client.OpenAI")
    def test_empty_response_exits(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(None)
        mock_openai_cls.return_value = mock_client

        with pytest.raises(SystemExit):
            call_llm("key", "gpt-4o", "sys", "usr")

    @patch("spicydiff.llm_client.OpenAI")
    def test_schema_validation_failure_exits(self, mock_openai_cls):
        # Valid JSON but invalid schema (score > 100)
        payload = {"summary": "Hi", "score": 999, "reviews": []}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
        mock_openai_cls.return_value = mock_client

        with pytest.raises(SystemExit):
            call_llm("key", "gpt-4o", "sys", "usr")
