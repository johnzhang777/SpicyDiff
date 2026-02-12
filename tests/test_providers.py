"""Unit tests for the providers module."""

import pytest

from spicydiff.providers import PROVIDERS, resolve_provider


class TestProviderRegistry:
    def test_all_presets_have_required_fields(self):
        for key, preset in PROVIDERS.items():
            assert preset.name, f"{key} missing name"
            assert preset.base_url.startswith("https://"), f"{key} base_url not https"
            assert preset.default_model, f"{key} missing default_model"
            assert preset.description, f"{key} missing description"

    def test_known_providers_exist(self):
        expected = {"openai", "deepseek", "qwen", "doubao", "zhipu", "moonshot", "gemini", "yi", "baichuan", "minimax"}
        assert expected.issubset(set(PROVIDERS.keys()))

    def test_claude_not_in_registry(self):
        """Claude is not OpenAI-compatible and should not be a built-in provider."""
        assert "claude" not in PROVIDERS

    def test_all_providers_are_openai_compatible(self):
        for key, preset in PROVIDERS.items():
            assert preset.openai_compatible is True, f"{key} is not marked as OpenAI-compatible"


class TestResolveProvider:
    # --- Provider shortcut ---
    def test_deepseek_shortcut(self):
        url, model = resolve_provider("deepseek", None, None)
        assert "deepseek" in url
        assert model == "deepseek-chat"

    def test_qwen_shortcut(self):
        url, model = resolve_provider("qwen", None, None)
        assert "dashscope" in url
        assert model == "qwen-plus"

    def test_doubao_shortcut(self):
        url, model = resolve_provider("doubao", None, None)
        assert "volces.com" in url
        assert model == "doubao-pro-32k"

    def test_gemini_shortcut(self):
        url, model = resolve_provider("gemini", None, None)
        assert "googleapis" in url
        assert "gemini" in model

    def test_zhipu_shortcut(self):
        url, model = resolve_provider("zhipu", None, None)
        assert "bigmodel" in url
        assert "glm" in model

    def test_moonshot_shortcut(self):
        url, model = resolve_provider("moonshot", None, None)
        assert "moonshot" in url

    def test_provider_with_model_override(self):
        url, model = resolve_provider("deepseek", None, "deepseek-coder")
        assert "deepseek" in url
        assert model == "deepseek-coder"

    def test_case_insensitive(self):
        url, model = resolve_provider("DeepSeek", None, None)
        assert "deepseek" in url

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            resolve_provider("not-a-real-provider", None, None)

    def test_claude_shortcut_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            resolve_provider("claude", None, None)

    # --- Explicit base_url always wins ---
    def test_explicit_base_url_overrides_provider(self):
        url, model = resolve_provider("deepseek", "https://my-proxy.com/v1", "my-model")
        assert url == "https://my-proxy.com/v1"
        assert model == "my-model"

    def test_explicit_base_url_without_model(self):
        url, model = resolve_provider(None, "https://custom.com/v1", None)
        assert url == "https://custom.com/v1"
        assert model == "gpt-4o"  # fallback

    # --- Default (no provider, no base_url) ---
    def test_default_is_openai(self):
        url, model = resolve_provider(None, None, None)
        assert "openai.com" in url
        assert model == "gpt-4o"

    def test_default_with_model_override(self):
        url, model = resolve_provider(None, None, "gpt-4o-mini")
        assert "openai.com" in url
        assert model == "gpt-4o-mini"
