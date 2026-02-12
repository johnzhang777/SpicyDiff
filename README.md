# SpicyDiff 🌶️

> LLM-powered code review with personality — **ROAST** or **PRAISE** your Pull Requests!

SpicyDiff is a GitHub Action that uses large language models to automatically review code changes in Pull Requests. Choose between two extreme personas:

| Mode | Personality | Style |
|------|------------|-------|
| **ROAST** 🔥 | Gordon Ramsay-style architect | Brutally sarcastic, kitchen metaphors, nitpicks everything |
| **PRAISE** 🌈 | Enthusiastic junior dev / hype squad leader | Blindly optimistic, emoji-heavy, hypes trivial code as genius |

## Supported LLM Providers

SpicyDiff works with **any OpenAI-compatible API**. Use the `provider` shortcut for one-line setup, or set `base-url` manually for custom endpoints.

| Provider | Shortcut | Default Model | Region |
|----------|----------|---------------|--------|
| **OpenAI** | `openai` | `gpt-4o` | Global |
| **DeepSeek** | `deepseek` | `deepseek-chat` | China / Global |
| **Alibaba Qwen** | `qwen` | `qwen-plus` | China |
| **ByteDance Doubao** | `doubao` | `doubao-pro-32k` | China |
| **Zhipu AI (GLM)** | `zhipu` | `glm-4-plus` | China |
| **Moonshot (Kimi)** | `moonshot` | `moonshot-v1-8k` | China |
| **01.AI (Yi)** | `yi` | `yi-large` | China |
| **Baichuan AI** | `baichuan` | `Baichuan4` | China |
| **MiniMax** | `minimax` | `abab6.5s-chat` | China |
| **Google Gemini** | `gemini` | `gemini-2.0-flash` | Global |
| **Anthropic Claude** | `claude` | `claude-sonnet-4-20250514` | Global |
| **Custom** | *(omit)* | *(set manually)* | Any |

---

## Quick Start

Create `.github/workflows/spicydiff.yml` in your repository:

### OpenAI (default)

```yaml
name: SpicyDiff Code Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.OPENAI_API_KEY }}
          mode: "ROAST"
          language: "en"
```

### DeepSeek

```yaml
      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.DEEPSEEK_API_KEY }}
          provider: "deepseek"
          mode: "ROAST"
          language: "zh"
```

### Alibaba Qwen (通义千问)

```yaml
      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.QWEN_API_KEY }}
          provider: "qwen"
          model: "qwen-max"          # optional: override default model
          mode: "PRAISE"
          language: "zh"
```

### ByteDance Doubao (豆包)

```yaml
      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.DOUBAO_API_KEY }}
          provider: "doubao"
          mode: "ROAST"
          language: "zh"
```

### Zhipu GLM (智谱)

```yaml
      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.ZHIPU_API_KEY }}
          provider: "zhipu"
          mode: "PRAISE"
          language: "zh"
```

### Google Gemini

```yaml
      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.GEMINI_API_KEY }}
          provider: "gemini"
          mode: "ROAST"
          language: "en"
```

### Custom / Self-hosted endpoint

```yaml
      - name: Run SpicyDiff
        uses: your-name/spicydiff@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.MY_API_KEY }}
          base-url: "https://my-company-proxy.internal/v1"
          model: "my-custom-model"
          mode: "ROAST"
          language: "zh"
```

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github-token` | Yes | — | GitHub token with `pull-requests: write` permission |
| `api-key` | Yes | — | API key for the LLM provider |
| `provider` | No | *(openai)* | Provider shortcut: `openai`, `deepseek`, `qwen`, `doubao`, `zhipu`, `moonshot`, `gemini`, `yi`, `baichuan`, `minimax` |
| `model` | No | *(per provider)* | Override the default model for the chosen provider |
| `mode` | No | `ROAST` | Review personality: `ROAST` or `PRAISE` |
| `language` | No | `en` | Output language: `zh` (中文) or `en` (English) |
| `base-url` | No | *(per provider)* | Custom base URL (overrides provider preset) |

**Priority rules:**
1. If `base-url` is set, it always wins (full manual control).
2. If `provider` is set, its preset URL is used; `model` can still be overridden.
3. If neither is set, defaults to OpenAI.

---

## How It Works

1. **Trigger** — Listens for PR `opened` or `synchronize` events.
2. **Fetch Diff** — Extracts `git diff`, filters out lock files, images, and binaries.
3. **LLM Analysis** — Sends the diff + persona prompt to the configured LLM.
4. **Parse Response** — Validates the structured JSON output via Pydantic.
5. **Post Feedback** — Publishes a **summary comment** (overall score + review) and **inline comments** on specific code lines.

---

## Development

### Prerequisites

- Python 3.9+
- Docker (for testing the Action locally)

### Setup

```bash
pip install -r requirements.txt
```

### Run Tests

```bash
pip install pytest
pytest tests/ -v
```

### Project Structure

```
SpicyDiff/
├── action.yml              # GitHub Action descriptor
├── Dockerfile              # Container image for the Action
├── requirements.txt        # Python dependencies
├── spicydiff/
│   ├── __init__.py
│   ├── __main__.py         # python -m spicydiff entry point
│   ├── main.py             # Pipeline orchestrator
│   ├── config.py           # Environment-based configuration
│   ├── models.py           # Pydantic data models
│   ├── providers.py        # LLM provider presets registry
│   ├── prompts.py          # ROAST / PRAISE prompt templates
│   ├── llm_client.py       # OpenAI-compatible LLM client
│   ├── diff_parser.py      # PR diff fetching & parsing
│   └── github_client.py    # GitHub comment posting
└── tests/
    ├── test_models.py
    ├── test_prompts.py
    ├── test_providers.py
    ├── test_diff_parser.py
    ├── test_github_client.py
    └── test_llm_client.py
```

## License

MIT
