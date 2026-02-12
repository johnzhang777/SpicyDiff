# SpicyDiff 🌶️

**AI code reviewer that roasts or praises your Pull Requests.**

SpicyDiff is a [GitHub Action](https://docs.github.com/en/actions). When someone opens a Pull Request in your repository, it automatically reads the code changes, sends them to an AI model, and posts review comments — either as a **brutally sarcastic chef** or a **blindly enthusiastic fan**.

| Mode | Personality | What it does |
|------|-------------|-------------|
| **ROAST** 🔥 | Gordon Ramsay-style senior architect | Roasts your code with kitchen metaphors. "This function is RAW!" |
| **PRAISE** 🌈 | Overly enthusiastic junior dev | Worships your code with emoji. "This for-loop is GENIUS! 🚀✨💖" |

---

## How to Use (3 Steps)

> You do NOT need to clone or install SpicyDiff. It runs automatically on GitHub's servers.

### Step 1: Get an API key from any LLM provider

You need an API key from **one** of these providers. Pick whichever you prefer:

| Provider | Where to get your API key | Recommended for |
|----------|--------------------------|-----------------|
| DeepSeek | https://platform.deepseek.com/api_keys | China (cheap & good) |
| Alibaba Qwen 通义千问 | https://dashscope.console.aliyun.com/apiKey | China |
| ByteDance Doubao 豆包 | https://console.volcengine.com/ark | China |
| Zhipu GLM 智谱 | https://open.bigmodel.cn/usercenter/apikeys | China |
| Moonshot Kimi | https://platform.moonshot.cn/console/api-keys | China |
| OpenAI | https://platform.openai.com/api-keys | Global |
| Google Gemini | https://aistudio.google.com/apikey | Global (free tier) |

### Step 2: Save the API key as a GitHub Secret

1. Go to **your repository** on GitHub (not SpicyDiff's repo — YOUR project's repo).
2. Click **Settings** (top menu bar).
3. In the left sidebar, click **Secrets and variables** > **Actions**.
4. Click the green **"New repository secret"** button.
5. Fill in:
   - **Name**: `LLM_API_KEY`
   - **Secret**: paste your API key from Step 1
6. Click **Add secret**.

> `GITHUB_TOKEN` is provided automatically by GitHub. You do NOT need to create it.

### Step 3: Create a workflow file

In **your repository**, create the file `.github/workflows/spicydiff.yml` with the following content.

Pick the example that matches your LLM provider:

<details>
<summary><b>DeepSeek</b> (recommended for China)</summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          provider: "deepseek"
          mode: "ROAST"
          language: "zh"
```

</details>

<details>
<summary><b>Alibaba Qwen 通义千问</b></summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          provider: "qwen"
          mode: "ROAST"
          language: "zh"
```

</details>

<details>
<summary><b>ByteDance Doubao 豆包</b></summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          provider: "doubao"
          mode: "ROAST"
          language: "zh"
```

</details>

<details>
<summary><b>Zhipu GLM 智谱</b></summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          provider: "zhipu"
          mode: "PRAISE"
          language: "zh"
```

</details>

<details>
<summary><b>Moonshot Kimi</b></summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          provider: "moonshot"
          mode: "ROAST"
          language: "zh"
```

</details>

<details>
<summary><b>OpenAI</b></summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          mode: "ROAST"
          language: "en"
```

> When no `provider` is specified, OpenAI is used by default.

</details>

<details>
<summary><b>Google Gemini</b></summary>

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
          api-key: ${{ secrets.LLM_API_KEY }}
          provider: "gemini"
          mode: "ROAST"
          language: "en"
```

</details>

<details>
<summary><b>Custom / Self-hosted endpoint</b></summary>

For any OpenAI-compatible API not listed above, set `base-url` and `model` manually:

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
          api-key: ${{ secrets.LLM_API_KEY }}
          base-url: "https://your-company-proxy.com/v1"
          model: "your-model-name"
          mode: "ROAST"
          language: "zh"
```

</details>

### Done!

Commit and push the file. Now, every time a Pull Request is opened or updated in your repository, SpicyDiff will automatically post a review.

---

## What the Review Looks Like

When SpicyDiff runs, it posts two types of comments on your PR:

### 1. Summary Comment (on the PR page)

> ## SpicyDiff Review 🗑️
>
> **Mode**: 🌶️ 地狱厨房模式 (ROAST)
> **Score**: 15/100 🗑️
>
> ---
>
> 这坨代码就像一碗放了三天的方便面——又糊又烂还发臭！变量命名像是蒙着眼在键盘上跳舞，嵌套深得像俄罗斯套娃，Magic Number 满天飞得像厨房里的苍蝇。我见过糟糕的代码，但这个让我想把显示器扔进油锅里！

### 2. Inline Comments (on specific code lines)

> 🌶️ **SpicyDiff**
>
> `x = 86400`? What is 86400? The number of times I want to slap whoever wrote this? USE A NAMED CONSTANT! This is the coding equivalent of unlabeled spice jars — nobody knows what's inside until it blows up!

---

## All Configuration Options

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github-token` | **Yes** | — | Always use `${{ secrets.GITHUB_TOKEN }}` (auto-provided by GitHub) |
| `api-key` | **Yes** | — | Your LLM provider's API key (saved as a GitHub Secret) |
| `provider` | No | `openai` | Provider shortcut (see table below) |
| `model` | No | *(auto)* | Override the default model. Each provider has a sensible default |
| `mode` | No | `ROAST` | `ROAST` = brutal critic, `PRAISE` = blind fan |
| `language` | No | `en` | `zh` = Chinese output, `en` = English output |
| `base-url` | No | *(auto)* | Custom API URL. If set, overrides `provider` |
| `temperature` | No | `0.7` | LLM sampling temperature (0.0 = deterministic, 1.0 = creative) |
| `max-tokens` | No | `4096` | Maximum tokens in the LLM response |
| `max-diff-chars` | No | `60000` | Maximum diff size (chars) sent to the LLM. Larger diffs are automatically truncated |
| `exclude-patterns` | No | — | Comma-separated glob patterns to skip (e.g. `"*.test.js,docs/**"`) |
| `pr-number` | No | *(auto)* | PR number (auto-detected; set manually for `workflow_dispatch`) |
| `dry-run` | No | `false` | If `true`, prints review to Action logs without posting to GitHub |

### Provider Shortcuts

Instead of remembering API URLs, just set `provider` to one of these:

| Shortcut | Provider | Default Model | API URL (auto-configured) |
|----------|----------|---------------|---------------------------|
| `openai` | OpenAI | `gpt-4o` | `api.openai.com` |
| `deepseek` | DeepSeek | `deepseek-chat` | `api.deepseek.com` |
| `qwen` | Alibaba Qwen | `qwen-plus` | `dashscope.aliyuncs.com` |
| `doubao` | ByteDance Doubao | `doubao-pro-32k` | `ark.cn-beijing.volces.com` |
| `zhipu` | Zhipu AI (GLM) | `glm-4-plus` | `open.bigmodel.cn` |
| `moonshot` | Moonshot (Kimi) | `moonshot-v1-8k` | `api.moonshot.cn` |
| `yi` | 01.AI (Yi) | `yi-large` | `api.lingyiwanwu.com` |
| `baichuan` | Baichuan AI | `Baichuan4` | `api.baichuan-ai.com` |
| `minimax` | MiniMax | `abab6.5s-chat` | `api.minimax.chat` |
| `gemini` | Google Gemini | `gemini-2.0-flash` | `generativelanguage.googleapis.com` |

> **Note on Claude:** Anthropic's API is not OpenAI-compatible. To use Claude, set up an OpenAI-compatible proxy (e.g. [LiteLLM](https://github.com/BerriAI/litellm) or [one-api](https://github.com/songquanpeng/one-api)) and configure `base-url` manually.

---

## FAQ

### Do I need to install anything?

**No.** SpicyDiff is a GitHub Action. GitHub downloads and runs it automatically. You only create a YAML config file.

### Do I need to clone / fork the SpicyDiff repository?

**No.** The line `uses: your-name/spicydiff@v1` in the YAML file tells GitHub to fetch it automatically.

### What is `GITHUB_TOKEN`? Do I need to create it?

**No.** `GITHUB_TOKEN` is automatically created by GitHub for every workflow run. Just use `${{ secrets.GITHUB_TOKEN }}` exactly as shown. You do NOT need to add it as a secret.

### What does `LLM_API_KEY` mean?

It's the name you chose when saving your API key in **Step 2**. You can name it anything (`OPENAI_KEY`, `DEEPSEEK_KEY`, etc.) — just make sure the name in the YAML matches:

```yaml
# If your secret is named MY_KEY:
api-key: ${{ secrets.MY_KEY }}
```

### I'm in China and can't access OpenAI. What do I use?

Use `provider: "deepseek"` or `provider: "qwen"` or `provider: "doubao"`. They all work in China without a VPN.

### How much does it cost?

- **GitHub Actions**: Free for public repos (2,000 minutes/month). Private repos have [free tier limits](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions).
- **LLM API**: Depends on your provider. DeepSeek and Gemini are very affordable. A typical PR review costs less than $0.01.

### Can I use a model not listed here?

Yes. Any service with an OpenAI-compatible API works. Set `base-url` and `model` manually:

```yaml
base-url: "https://your-api.com/v1"
model: "your-model-name"
```

### Can I change the review mode per PR?

Not dynamically — the mode is set in the YAML file. But you can create two workflow files if you want both:

```
.github/workflows/spicydiff-roast.yml   # mode: "ROAST"
.github/workflows/spicydiff-praise.yml  # mode: "PRAISE"
```

### How do I test without posting comments?

Use dry-run mode. It prints the full review to the Action logs without touching the PR:

```yaml
dry-run: "true"
```

### My PR is huge. Will SpicyDiff crash?

No. Diffs are automatically truncated to 60,000 characters (~15k tokens) by default. You can adjust this with `max-diff-chars`. Files beyond the limit are skipped, and the LLM is told which files were omitted.

### Can I exclude test files or documentation?

Yes. Use `exclude-patterns` with comma-separated globs:

```yaml
exclude-patterns: "*.test.js,*.spec.ts,docs/**"
```

### Can I use Anthropic Claude?

Not directly — the Anthropic API is not OpenAI-compatible. Use an OpenAI-compatible proxy like [LiteLLM](https://github.com/BerriAI/litellm) or [one-api](https://github.com/songquanpeng/one-api), then set `base-url` to your proxy.

---

## How It Works (Behind the Scenes)

```
You open a Pull Request
       │
       ▼
GitHub sees your .github/workflows/spicydiff.yml
       │
       ▼
GitHub downloads SpicyDiff and builds its Docker container
       │
       ▼
SpicyDiff reads the code changes (git diff) from your PR
       │
       ▼
It sends the diff to the AI with a "roast" or "praise" personality prompt
       │
       ▼
The AI returns a JSON response with a score and line-by-line comments
       │
       ▼
SpicyDiff posts the review as comments on your PR
       │
       ▼
Done! The container shuts down. Nothing stays running.
```

---

## For Contributors

If you want to contribute to SpicyDiff itself:

### Prerequisites

- Python 3.9+
- Docker (optional, for testing the container)

### Setup

```bash
git clone https://github.com/your-name/spicydiff.git
cd spicydiff
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
├── Dockerfile              # Container image (non-root)
├── requirements.txt        # Python dependencies
├── .github/workflows/
│   └── ci.yml              # CI: tests on Python 3.9–3.12, lint, Docker build
├── spicydiff/
│   ├── __init__.py
│   ├── __main__.py         # python -m spicydiff entry point
│   ├── main.py             # Pipeline orchestrator (with dry-run support)
│   ├── config.py           # Reads all configuration from environment
│   ├── models.py           # Data models (Pydantic)
│   ├── providers.py        # LLM provider presets (10 built-in providers)
│   ├── prompts.py          # ROAST / PRAISE prompt templates (zh + en)
│   ├── llm_client.py       # LLM API with retry, timeout, fence stripping
│   ├── diff_parser.py      # PR diff with size limits + custom excludes
│   ├── github_client.py    # GitHub comments with retry + i18n labels
│   └── logger.py           # Structured logging with GitHub Actions annotations
└── tests/                  # 106 unit tests
```

---

## License

MIT
