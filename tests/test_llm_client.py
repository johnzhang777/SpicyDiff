"""Unit tests for the llm_client module (with mocked OpenAI calls)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from spicydiff.llm_client import call_llm, _strip_code_fences
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
        payload = {"summary": "Hi", "score": 999, "reviews": []}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
        mock_openai_cls.return_value = mock_client

        with pytest.raises(SystemExit):
            call_llm("key", "gpt-4o", "sys", "usr")

    @patch("spicydiff.llm_client.OpenAI")
    def test_api_exception_exits(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection refused")
        mock_openai_cls.return_value = mock_client

        with pytest.raises(SystemExit):
            call_llm("key", "gpt-4o", "sys", "usr")

    @patch("spicydiff.llm_client.OpenAI")
    def test_passes_retry_and_timeout(self, mock_openai_cls):
        """Verify that max_retries and timeout are passed to the OpenAI client."""
        payload = {"summary": "OK", "score": 50, "reviews": []}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
        mock_openai_cls.return_value = mock_client

        call_llm("key", "gpt-4o", "sys", "usr", max_retries=5, timeout=60)

        # Check the OpenAI constructor was called with retry/timeout args
        mock_openai_cls.assert_called_once_with(
            api_key="key",
            base_url="https://api.openai.com/v1",
            max_retries=5,
            timeout=60,
        )

    @patch("spicydiff.llm_client.OpenAI")
    def test_passes_temperature_and_max_tokens(self, mock_openai_cls):
        payload = {"summary": "OK", "score": 50, "reviews": []}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(json.dumps(payload))
        mock_openai_cls.return_value = mock_client

        call_llm("key", "gpt-4o", "sys", "usr", temperature=0.3, max_tokens=2048)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.3
        assert call_args.kwargs["max_tokens"] == 2048


class TestStripCodeFences:
    def test_json_fence(self):
        assert _strip_code_fences("```json\n{}\n```") == "{}"

    def test_plain_fence(self):
        assert _strip_code_fences("```\n{}\n```") == "{}"

    def test_no_fence(self):
        assert _strip_code_fences('{"a": 1}') == '{"a": 1}'

    def test_whitespace(self):
        assert _strip_code_fences("  ```json\n{}\n```  ") == "{}"

    def test_only_opening_fence(self):
        result = _strip_code_fences("```json\n{}")
        assert result == "{}"

    def test_nested_backticks_in_content(self):
        content = '```json\n{"code": "use `x`"}\n```'
        result = _strip_code_fences(content)
        assert '"code"' in result
