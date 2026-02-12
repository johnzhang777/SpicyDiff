"""Built-in LLM provider presets.

Users can either pick a provider shortcut (e.g. provider: "deepseek") or
manually specify openai-base-url + model for any OpenAI-compatible service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ProviderPreset:
    """Pre-configured defaults for a known LLM provider."""

    name: str
    base_url: str
    default_model: str
    description: str


# ---------------------------------------------------------------------------
# Registry of supported providers
# Key = lowercase shortcut name used in the `provider` input
# ---------------------------------------------------------------------------
PROVIDERS: Dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        description="OpenAI GPT models (gpt-4o, gpt-4o-mini, etc.)",
    ),
    "deepseek": ProviderPreset(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        description="DeepSeek models (deepseek-chat, deepseek-coder, etc.)",
    ),
    "qwen": ProviderPreset(
        name="Alibaba Qwen (DashScope)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        description="Alibaba Qwen models via DashScope (qwen-plus, qwen-turbo, qwen-max, etc.)",
    ),
    "doubao": ProviderPreset(
        name="ByteDance Doubao (Ark)",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        default_model="doubao-pro-32k",
        description="ByteDance Doubao models via Volcano Ark (doubao-pro-32k, doubao-lite-32k, etc.)",
    ),
    "zhipu": ProviderPreset(
        name="Zhipu AI (GLM)",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-plus",
        description="Zhipu GLM models (glm-4-plus, glm-4-flash, etc.)",
    ),
    "moonshot": ProviderPreset(
        name="Moonshot AI (Kimi)",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        description="Moonshot Kimi models (moonshot-v1-8k, moonshot-v1-32k, etc.)",
    ),
    "yi": ProviderPreset(
        name="01.AI (Yi)",
        base_url="https://api.lingyiwanwu.com/v1",
        default_model="yi-large",
        description="01.AI Yi models (yi-large, yi-medium, yi-spark, etc.)",
    ),
    "baichuan": ProviderPreset(
        name="Baichuan AI",
        base_url="https://api.baichuan-ai.com/v1",
        default_model="Baichuan4",
        description="Baichuan models (Baichuan4, Baichuan3-Turbo, etc.)",
    ),
    "minimax": ProviderPreset(
        name="MiniMax",
        base_url="https://api.minimax.chat/v1",
        default_model="abab6.5s-chat",
        description="MiniMax models (abab6.5s-chat, abab5.5-chat, etc.)",
    ),
    "gemini": ProviderPreset(
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.0-flash",
        description="Google Gemini models via OpenAI-compatible endpoint (gemini-2.0-flash, gemini-1.5-pro, etc.)",
    ),
    "claude": ProviderPreset(
        name="Anthropic Claude",
        base_url="https://api.anthropic.com/v1",
        default_model="claude-sonnet-4-20250514",
        description="Anthropic Claude models (requires anthropic-compatible proxy or adapter)",
    ),
}


def resolve_provider(
    provider: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
) -> tuple[str, str]:
    """Resolve the final (base_url, model) from user inputs.

    Priority:
    1. Explicit base_url + model always win (full manual control).
    2. If provider is set, use its preset defaults, but allow model override.
    3. Fall back to OpenAI defaults.

    Returns
    -------
    (base_url, model)
    """
    # Case 1: User explicitly set base_url — they know what they're doing
    if base_url:
        return base_url, model or "gpt-4o"

    # Case 2: Provider shortcut
    if provider:
        key = provider.strip().lower()
        preset = PROVIDERS.get(key)
        if preset is None:
            available = ", ".join(sorted(PROVIDERS.keys()))
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Available providers: {available}. "
                f"Or set openai-base-url manually for custom endpoints."
            )
        return preset.base_url, model or preset.default_model

    # Case 3: Default to OpenAI
    default = PROVIDERS["openai"]
    return default.base_url, model or default.default_model
