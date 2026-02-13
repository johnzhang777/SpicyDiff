# SpicyDiff Architecture & Technical Manual

> A detailed guide to how SpicyDiff works internally — for contributors, curious developers, and anyone who wants to understand the principles behind the project.

---

## Table of Contents

1. [What is SpicyDiff?](#1-what-is-spicydiff)
2. [How GitHub Actions Work (Background)](#2-how-github-actions-work)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Complete Execution Flow](#4-complete-execution-flow)
5. [Module Deep Dive](#5-module-deep-dive)
   - 5.1 [Entry Point & Orchestration (`main.py`)](#51-entry-point--orchestration)
   - 5.2 [Configuration Layer (`config.py` + `repo_config.py`)](#52-configuration-layer)
   - 5.3 [LLM Provider System (`providers.py`)](#53-llm-provider-system)
   - 5.4 [Diff Parsing (`diff_parser.py`)](#54-diff-parsing)
   - 5.5 [Smart Context Extraction (`context.py`)](#55-smart-context-extraction)
   - 5.6 [Prompt Engineering (`prompts.py`)](#56-prompt-engineering)
   - 5.7 [LLM Client (`llm_client.py`)](#57-llm-client)
   - 5.8 [GitHub Comment Posting (`github_client.py`)](#58-github-comment-posting)
   - 5.9 [Data Models (`models.py`)](#59-data-models)
   - 5.10 [Logging (`logger.py`)](#510-logging)
6. [Review Strategies](#6-review-strategies)
7. [Prompt Engineering Principles](#7-prompt-engineering-principles)
8. [Docker & Deployment](#8-docker--deployment)
9. [Module Dependency Graph](#9-module-dependency-graph)
10. [Configuration Priority & Merging](#10-configuration-priority--merging)
11. [Error Handling & Resilience](#11-error-handling--resilience)
12. [Testing Strategy](#12-testing-strategy)

---

## 1. What is SpicyDiff?

SpicyDiff is a **GitHub Action** that uses Large Language Models (LLMs) to automatically review code changes in Pull Requests. It reads the `git diff`, sends it to an AI model with a personality prompt, and posts the review as a comment on the PR.

What makes it unique:

- **Personality-driven reviews**: Three modes (ROAST / PRAISE / SECURITY) give the AI different personas
- **Multi-provider support**: Works with 10+ LLM providers (DeepSeek, Qwen, OpenAI, Gemini, etc.)
- **Smart multi-file review**: Large PRs are reviewed file-by-file with surrounding code context
- **Team-customizable rules**: Teams define their own coding standards via `.spicydiff.yml`

---

## 2. How GitHub Actions Work

Understanding SpicyDiff requires understanding how GitHub Actions work:

```
┌──────────────────────────────────────────────────────────────┐
│                     Developer's Repository                   │
│                                                              │
│  .github/workflows/spicydiff.yml     ← Workflow definition   │
│  src/                                ← Their code            │
│  .spicydiff.yml                      ← Optional team config  │
└──────────────┬───────────────────────────────────────────────┘
               │  PR opened / updated
               ▼
┌──────────────────────────────────────────────────────────────┐
│                     GitHub Actions Runner                    │
│                                                              │
│  1. Reads spicydiff.yml workflow                             │
│  2. Sees: uses: johnzhang777/spicydiff@v1                    │
│  3. Downloads SpicyDiff repo at tag v1                       │
│  4. Builds Docker image from Dockerfile                      │
│  5. Runs the container with INPUT_* environment variables    │
│  6. Container exits → runner cleans up                       │
└──────────────────────────────────────────────────────────────┘
```

Key points:
- SpicyDiff runs as a **Docker container** on GitHub's infrastructure
- The developer never installs or deploys anything
- GitHub passes all `with:` inputs as `INPUT_*` environment variables
- GitHub also injects context variables like `GITHUB_REPOSITORY`, `GITHUB_EVENT_PATH`, etc.

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SpicyDiff Container                          │
│                                                                     │
│  entrypoint.sh                                                      │
│  └── python -m spicydiff.main                                       │
│       │                                                             │
│       ├── config.py ←── repo_config.py ←── .spicydiff.yml           │
│       │       └── providers.py                                      │
│       │                                                             │
│       ├── diff_parser.py ──── GitHub API ──── PR files + patches    │
│       │                                                             │
│       ├── context.py ──── GitHub API ──── full file contents        │
│       │                                                             │
│       ├── prompts.py ──── builds system + user prompts              │
│       │                                                             │
│       ├── llm_client.py ──── LLM API ──── AI response (JSON)        │
│       │                                                             │
│       └── github_client.py ──── GitHub API ──── PR comment          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**External dependencies:**
- **GitHub API** (via PyGithub): Read PR diff, fetch file contents, post comments
- **LLM API** (via OpenAI SDK): Send prompts, receive structured JSON reviews
- **Docker**: Container runtime provided by GitHub Actions

---

## 4. Complete Execution Flow

Here is exactly what happens, step by step, from the moment a PR is opened:

### Phase 0: Trigger & Container Start

```
Developer opens PR → GitHub reads .github/workflows/spicydiff.yml
→ GitHub builds Docker image from Dockerfile
→ Docker starts container with --workdir /github/workspace
→ entrypoint.sh sets PYTHONPATH=/app
→ python -m spicydiff.main → calls main()
```

### Phase 1: Resolve PR Number

```python
# main.py: _resolve_pr_number()
```

GitHub provides the event payload at `GITHUB_EVENT_PATH` (a JSON file). SpicyDiff reads this file to extract the PR number:

```json
{
  "pull_request": {
    "number": 42,
    ...
  }
}
```

The PR number is stored in the `PR_NUMBER` environment variable for later use by `config.py`.

### Phase 2: Load Configuration

```python
# config.py: Config.from_env()
```

Configuration comes from **three sources**, merged in priority order:

```
Priority 1 (highest): GitHub Action inputs (INPUT_* env vars)
Priority 2:           .spicydiff.yml in the user's repo
Priority 3 (lowest):  Built-in defaults
```

The process:
1. Read required inputs: `INPUT_GITHUB_TOKEN`, `INPUT_API_KEY`
2. Resolve the LLM provider (see Section 5.3)
3. Load `.spicydiff.yml` from the workspace (if it exists)
4. Merge all settings into a frozen `Config` dataclass

### Phase 3: Fetch & Parse PR Diff

```python
# diff_parser.py: get_pr() + fetch_pr_diff()
```

1. Connect to GitHub API using `PyGithub`
2. Fetch the PR object by repository name + PR number
3. Iterate through all changed files in the PR
4. For each file:
   - Check against ignore patterns (lock files, images, binaries)
   - Check against user-provided exclude patterns
   - Check if adding this file exceeds `max_diff_chars` budget
   - Parse the unified diff with `unidiff` to extract added line numbers
5. Return a `PRDiff` containing all `FileDiff` objects

```
PR has 20 files
  ├── package-lock.json    → SKIP (built-in ignore)
  ├── logo.png             → SKIP (binary)
  ├── *.test.js            → SKIP (user exclude pattern)
  ├── src/main.py          → INCLUDE (2,400 chars)
  ├── src/utils.py          → INCLUDE (1,800 chars)
  ├── ...
  └── src/huge-file.py     → SKIP (would exceed 60,000 char budget)
                               PRDiff.truncated = True
```

### Phase 4: Choose Review Strategy

```python
# main.py: run()
if len(pr_diff.files) <= MULTI_FILE_THRESHOLD:  # default: 3
    result = _single_pass_review(...)
else:
    result = _multi_file_review(...)
```

Two strategies:

| Strategy | When | How | LLM calls |
|----------|------|-----|-----------|
| **Single-pass** | ≤3 files | Send entire diff in one prompt | 1 |
| **Multi-file** | 4+ files | Review each file individually, then merge | N + 1 |

See [Section 6](#6-review-strategies) for details.

### Phase 5: Build Prompts

```python
# prompts.py: build_system_prompt() + build_user_prompt()
```

The system prompt is assembled from four pieces:

```
┌────────────────────────────────────────────┐
│ System Prompt                              │
│                                            │
│ 1. System Context (JSON format rules)      │
│ 2. Persona (ROAST / PRAISE / SECURITY)     │
│ 3. Custom Rules (from .spicydiff.yml)      │
│ 4. Output Schema (JSON structure)          │
└────────────────────────────────────────────┘
```

The user prompt contains the diff:

```
┌─────────────────────────────────────────────┐
│ User Prompt                                 │
│                                             │
│ "Please review the following code changes:" │
│                                             │
│ ```diff                                     │
│ --- a/src/main.py                           │
│ +++ b/src/main.py                           │
│ @@ -10,3 +10,5 @@                           │
│ +    x = 86400                              │
│ +    if True:                               │
│ ```                                         │
│                                             │
│ (optional: smart context block)             │
│ (optional: truncation notice)               │
└─────────────────────────────────────────────┘
```

### Phase 6: Call LLM

```python
# llm_client.py: call_llm()
```

1. Create an OpenAI client pointed at the provider's base URL
2. Send the system + user prompts via `chat.completions.create()`
3. The LLM returns raw text (supposed to be JSON)
4. Strip any markdown code fences (```` ```json ... ``` ````)
5. Parse as JSON
6. Validate against the Pydantic `ReviewResult` schema
7. Return the structured result

```
LLM Response (raw text):
```json
{
  "summary": "这代码像没煮熟的牛排!",
  "score": 25,
  "reviews": [
    {"file_path": "src/main.py", "line_number": 10, "comment": "Magic number!"}
  ]
}
```
→ Strip fences → Parse JSON → Validate schema → ReviewResult object
```

### Phase 7: Post Results

```python
# github_client.py: post_summary_comment()
```

Everything is posted as **one single comment** on the PR:

```
┌───────────────────────────────────────────┐
│ ## SpicyDiff Review 🔥                    │
│ Mode: 🌶️ 地狱厨房模式 (ROAST)               │
│ Score: 35/100 🔥                          │
│ ─────────────────────                     │
│ Overall summary text...                   │
│                                           │
│ ### 📂 文件审查详情                         │
│                                           │
│ ▶ src/main.py    —  25/100  🗑️            │
│   (click to expand full review)           │
│                                           │
│ ▶ src/utils.py   —  50/100  😐            │
│   (click to expand full review)           │
└───────────────────────────────────────────┘
```

The comment uses a hidden HTML marker (`<!-- spicydiff-review -->`) so that on subsequent PR updates, SpicyDiff finds and **updates** the existing comment instead of creating a new one.

---

## 5. Module Deep Dive

### 5.1 Entry Point & Orchestration

**Files:** `__main__.py`, `main.py`, `entrypoint.sh`

`entrypoint.sh` is the Docker container's entry point. It sets `PYTHONPATH=/app` (critical because GitHub Actions overrides the working directory to `/github/workspace`) and then runs `python -m spicydiff.main`.

`main.py` contains the `run()` function, which is the pipeline orchestrator. It follows a strict 5-step sequence:

1. Resolve PR number from event context
2. Load configuration (env vars + repo config)
3. Fetch and parse the PR diff
4. Choose and execute the review strategy (single-pass or multi-file)
5. Post the result as a GitHub comment (or log it in dry-run mode)

All imports are done lazily inside `run()` so that if a dependency is missing, the error message is clear.

### 5.2 Configuration Layer

**Files:** `config.py`, `repo_config.py`

The configuration system has two layers:

**Layer 1: `config.py`** — Reads `INPUT_*` environment variables that GitHub Actions injects from the `with:` block in the workflow YAML.

**Layer 2: `repo_config.py`** — Optionally loads a `.spicydiff.yml` file from the user's repository root. This allows teams to commit shared settings (mode, language, custom rules, exclude patterns) alongside their code.

**Merging logic:**

```python
# Pseudo-code for the merge
final_mode = action_input_mode or repo_config_mode or "ROAST"
final_language = action_input_language or repo_config_language or "en"
final_exclude = action_input_exclude + repo_config_exclude  # combined
final_rules = action_input_rules + repo_config_rules         # combined
```

Action inputs always win. Repo config provides team defaults. Built-in defaults are the fallback.

### 5.3 LLM Provider System

**File:** `providers.py`

SpicyDiff supports any LLM with an OpenAI-compatible API. The provider system has three tiers:

```
Tier 1: Provider shortcut     → provider: "deepseek"
Tier 2: Manual base URL       → base-url: "https://custom.com/v1"
Tier 3: Default (OpenAI)      → (no provider or base-url set)
```

The `PROVIDERS` dictionary maps shortcut names to `ProviderPreset` objects:

```python
"deepseek" → ProviderPreset(
    base_url="https://api.deepseek.com/v1",
    default_model="deepseek-chat",
)
```

The `resolve_provider()` function implements the priority chain:

```
explicit base_url wins → provider shortcut → default (OpenAI)
```

**Why this works for all providers:** Most modern LLM providers (DeepSeek, Qwen, Zhipu, Moonshot, etc.) expose OpenAI-compatible APIs — they accept the same request format and return the same response format. So one `openai.OpenAI(base_url=...)` client works for all of them.

### 5.4 Diff Parsing

**File:** `diff_parser.py`

This module fetches the PR diff from GitHub and transforms it into structured data.

**Step 1: File filtering**

Files are filtered through two layers:
- **Built-in regex patterns**: Lock files (`package-lock.json`, `yarn.lock`, `Cargo.lock`, etc.), binary files (`.png`, `.pdf`, `.woff2`, etc.), OS files (`.DS_Store`)
- **User glob patterns**: From `exclude-patterns` input or `.spicydiff.yml` `exclude` list

**Step 2: Size budgeting**

The total diff size is capped at `max_diff_chars` (default 60,000 characters ≈ 15,000 tokens). Files are added in order; once the budget is exhausted, remaining files are skipped and `PRDiff.truncated` is set to `True`.

**Step 3: Line number extraction**

For each included file, the `unidiff` library parses the patch text to extract which line numbers in the new file were added or modified. This information is stored as `added_lines: Dict[int, str]` — a mapping of line numbers to their content.

This is used later for:
- Smart context extraction (which function contains the changed lines?)
- Line-level comment validation (is the LLM's line number actually in the diff?)

### 5.5 Smart Context Extraction

**File:** `context.py`

When reviewing a single file (in multi-file mode), just seeing the diff isn't enough — the LLM needs to understand the **surrounding code** to give useful feedback.

**How it works:**

1. Fetch the full file content from GitHub at the PR's head commit
2. For each changed line, find the **enclosing function or class** using:
   - Indentation analysis (walk backwards to find a line with less indentation)
   - Block pattern matching (regex patterns for `def`, `function`, `class`, `func`, `pub fn`, etc.)
3. Merge overlapping ranges (if two changes are in the same function, extract it once)
4. Truncate to `MAX_CONTEXT_CHARS` (3,000) to avoid bloating the prompt

**Example:**

```python
# The LLM sees this context:
  10 | def calculate_total(items):
  11 |     total = 0
  12 |     for item in items:
  13 |         total += item.price * item.quantity  # ← changed line
  14 |     return total

# Instead of just:
@@ -13 +13 @@
+         total += item.price * item.quantity
```

The context makes a huge difference — the LLM can now understand that `total` is an accumulator, `items` is iterable, and the function returns a sum.

**Supported languages:** Python, JavaScript/TypeScript, Go, Java/C#/Kotlin, Rust (via block pattern regex).

### 5.6 Prompt Engineering

**File:** `prompts.py`

The prompt system is built from modular, internationalized components.

**System prompt structure:**

```
┌─────────────────────────────────────────┐
│ 1. System Context                        │
│    "You are a code review assistant.     │
│     Output strict JSON only..."          │
├─────────────────────────────────────────┤
│ 2. Persona (mode-dependent)              │
│    ROAST: "Gordon Ramsay-style..."       │
│    PRAISE: "Enthusiastic junior dev..."  │
│    SECURITY: "Paranoid auditor..."       │
├─────────────────────────────────────────┤
│ 3. Custom Rules (optional)               │
│    "Also check these team rules:         │
│     1. All functions need docstrings     │
│     2. No hardcoded URLs"               │
├─────────────────────────────────────────┤
│ 4. Output Schema                         │
│    "Return JSON: {summary, score,        │
│     reviews: [{file_path, line_number,   │
│     comment}]}"                          │
└─────────────────────────────────────────┘
```

Every section has zh and en variants. The language parameter determines which variant is used for **all** sections — not just the persona.

**Four prompt builders:**

| Function | Used in | Purpose |
|----------|---------|---------|
| `build_system_prompt()` | All modes | Builds the complete system instruction |
| `build_user_prompt()` | Single-pass | Sends the entire diff at once |
| `build_file_review_prompt()` | Multi-file | Sends one file's diff + context |
| `build_merge_summary_prompt()` | Multi-file | Asks LLM to merge per-file reviews |

### 5.7 LLM Client

**File:** `llm_client.py`

A thin wrapper around the OpenAI SDK with added resilience.

**Features:**
- **Automatic retry**: The `openai` SDK's built-in retry (default 3 retries with exponential backoff) handles 429 (rate limit) and 5xx (server error)
- **Configurable timeout**: Default 120 seconds per request
- **Code fence stripping**: Some models return `` ```json ... ``` `` despite being told not to — we strip these before parsing
- **Schema validation**: The JSON response is validated against the `ReviewResult` Pydantic model

**Error handling chain:**

```
API call fails → retry 3 times → still fails → sys.exit(1)
Response empty → sys.exit(1)
JSON parse fails → log raw output → sys.exit(1)
Schema invalid (e.g. score=999) → log validation error → sys.exit(1)
All good → return ReviewResult
```

### 5.8 GitHub Comment Posting

**File:** `github_client.py`

Posts one unified comment containing the entire review.

**Comment structure (multi-file mode):**

```markdown
<!-- spicydiff-review -->          ← hidden marker for identification
## SpicyDiff Review 🔥
**Mode**: 🌶️ Hell's Kitchen (ROAST)
**Score**: 35/100 🔥
---
Overall summary from merge call...

### 📂 Per-file Review Details

<details>
<summary><b><code>src/main.py</code></b> — 25/100 🗑️</summary>

Full review text for this file...

**Line Comments:**
- **L10**: Magic number 86400 — use a named constant!
- **L23**: Nesting 5 levels deep — refactor this!

</details>

<details>
<summary><b><code>src/utils.py</code></b> — 50/100 😐</summary>

Full review text for this file...

**Line Comments:**
- **L45**: Bare except — catch specific exceptions!

</details>
```

**Comment update logic:**
1. Search existing PR comments for the `<!-- spicydiff-review -->` marker
2. If found → **edit** the existing comment (avoids spam on re-runs)
3. If not found → **create** a new comment

**Score emoji mapping:**

| Score | Emoji |
|-------|-------|
| 0–19 | 🗑️ |
| 20–39 | 🔥 |
| 40–59 | 😐 |
| 60–79 | 👍 |
| 80–100 | 🚀 |

### 5.9 Data Models

**File:** `models.py`

Pydantic models ensure type safety and validation:

```
Mode (Enum)
├── ROAST
├── PRAISE
└── SECURITY

Language (Enum)
├── ZH
└── EN

InlineReview
├── file_path: str
├── line_number: int (≥1)
└── comment: str (non-empty)

ReviewResult (LLM returns this)
├── summary: str (non-empty)
├── score: int (0-100)
└── reviews: List[InlineReview]

FileReviewSummary (per-file metadata)
├── file_path: str
├── score: int
├── summary: str
└── comment_count: int

FullReviewResult (multi-file aggregate)
├── summary: str
├── score: int
├── reviews: List[InlineReview]
└── file_summaries: List[FileReviewSummary]
```

### 5.10 Logging

**File:** `logger.py`

A custom logger that maps Python log levels to GitHub Actions annotations:

| Python level | GitHub Actions output |
|---|---|
| `log.info("msg")` | `msg` |
| `log.warning("msg")` | `::warning::msg` |
| `log.error("msg")` | `::error::msg` |

GitHub Actions renders `::warning::` and `::error::` as yellow/red annotations in the workflow run log, making issues easy to spot.

---

## 6. Review Strategies

### Single-pass (≤3 files)

```
All file diffs → concatenate → one prompt → one LLM call → ReviewResult
```

**Pros:** Fast, cheap (1 API call), simple.
**Cons:** LLM may lose focus with multiple files in one prompt.

### Multi-file (4+ files)

```
File 1 diff + context → LLM call → FileResult 1
File 2 diff + context → LLM call → FileResult 2
...
File N diff + context → LLM call → FileResult N
                                        │
All FileResults → merge prompt → LLM call → FullReviewResult
```

**Pros:** Each file gets focused attention. Smart context helps the LLM understand the code. Per-file summaries are preserved in the final comment.
**Cons:** More API calls (N+1), more expensive, slower.

**The threshold** (`MULTI_FILE_THRESHOLD = 3`) is a balance between quality and cost. Users can't change it currently, but it can be adjusted in the source code.

---

## 7. Prompt Engineering Principles

### 7.1 Strict JSON Output

The system prompt explicitly tells the LLM:
- Output pure JSON only
- No markdown code fences
- No extra fields

Despite this, some models still add `` ```json `` wrappers — hence the `_strip_code_fences()` fallback in `llm_client.py`.

### 7.2 Persona Consistency

Each mode has a carefully crafted persona that maintains the character throughout:
- **ROAST**: Insults use cooking/kitchen metaphors consistently (not random insults)
- **PRAISE**: Over-the-top enthusiasm with specific emoji patterns
- **SECURITY**: Professional audit report tone with severity tags

### 7.3 Line Number Accuracy

The prompt explicitly instructs the LLM to use **new file line numbers** (the `+++` side of the diff), not diff offsets. This is clarified in both languages to reduce errors.

### 7.4 Custom Rules Injection

Team rules are injected between the persona and the output schema:

```
[persona instructions]

In addition to the above, also check these team rules:
1. All functions must have docstrings
2. No hardcoded URLs

[JSON output schema]
```

This placement ensures the LLM treats custom rules with the same importance as the built-in review criteria.

---

## 8. Docker & Deployment

### Container Structure

```
/app/                           ← PYTHONPATH points here
├── requirements.txt
├── entrypoint.sh               ← ENTRYPOINT (sets PYTHONPATH, runs Python)
└── spicydiff/
    ├── __init__.py
    ├── __main__.py
    ├── main.py
    └── ... (all modules)

/github/workspace/              ← GitHub's --workdir (user's repo)
├── .github/workflows/
├── .spicydiff.yml              ← repo config loaded from here
├── src/
└── ...
```

### Why `entrypoint.sh` is needed

GitHub Actions overrides the Docker `WORKDIR` to `/github/workspace` (the user's repository). Without `entrypoint.sh` setting `PYTHONPATH=/app`, Python would look for `spicydiff` in `/github/workspace/` and fail with `ModuleNotFoundError`.

### Security

The container runs as non-root user `spicydiff` (UID 1001) for security best practices.

---

## 9. Module Dependency Graph

```
main.py
├── config.py
│   ├── models.py (Mode, Language)
│   ├── providers.py (resolve_provider)
│   └── repo_config.py (.spicydiff.yml)
│       └── logger.py
├── diff_parser.py (PyGithub + unidiff)
│   └── logger.py
├── context.py (PyGithub)
│   └── logger.py
├── prompts.py
│   └── models.py (Mode, Language)
├── llm_client.py (openai SDK)
│   ├── models.py (ReviewResult)
│   └── logger.py
├── github_client.py (PyGithub)
│   ├── models.py (Mode, Language, ReviewResult, FullReviewResult)
│   └── logger.py
└── logger.py
```

**External library usage:**
- `PyGithub` → GitHub API (diff_parser, context, github_client)
- `openai` → LLM API (llm_client)
- `unidiff` → Git diff parsing (diff_parser)
- `pydantic` → Data validation (models)
- `PyYAML` → Config file parsing (repo_config)

---

## 10. Configuration Priority & Merging

```
┌─────────────────────────────────────────────┐
│         Priority 1: Action Inputs            │
│  (from workflow YAML `with:` block)          │
│  e.g. mode: "SECURITY"                       │
├─────────────────────────────────────────────┤
│         Priority 2: .spicydiff.yml           │
│  (from user's repo root)                     │
│  e.g. mode: ROAST, rules: [...]              │
├─────────────────────────────────────────────┤
│         Priority 3: Built-in Defaults        │
│  mode=ROAST, language=en, temp=0.7           │
│  max_tokens=4096, max_diff_chars=60000       │
└─────────────────────────────────────────────┘
```

**List fields** (exclude patterns, custom rules) are **merged** from both sources rather than overridden — so a team can set base rules in `.spicydiff.yml` and a workflow can add more.

---

## 11. Error Handling & Resilience

| Error | Handling |
|-------|----------|
| Missing required env var | `sys.exit(1)` with `::error::` annotation |
| Invalid provider name | `sys.exit(1)` listing available providers |
| LLM API timeout | OpenAI SDK retries 3 times with backoff |
| LLM API rate limit (429) | OpenAI SDK retries automatically |
| LLM returns non-JSON | Log raw output, `sys.exit(1)` |
| LLM returns invalid schema | Log validation error, `sys.exit(1)` |
| GitHub API rate limit (429) | Custom retry with exponential backoff |
| GitHub API permission denied (403) | Log warning, do not retry |
| Diff parsing fails (unidiff) | Log warning, include raw patch anyway |
| `.spicydiff.yml` invalid | Log warning, use defaults |
| No reviewable files in PR | Log info, exit cleanly (success) |

---

## 12. Testing Strategy

**142 unit tests** covering all modules:

| Test file | What it tests |
|-----------|--------------|
| `test_models.py` | Pydantic validation (valid/invalid scores, empty summaries, etc.) |
| `test_providers.py` | Provider resolution, shortcuts, case-insensitivity, unknown providers |
| `test_prompts.py` | All prompt builders × all modes × all languages, custom rules injection |
| `test_diff_parser.py` | File ignore patterns, glob matching, size truncation, data classes |
| `test_context.py` | Block detection, range merging, truncation, multi-language patterns |
| `test_llm_client.py` | Mock OpenAI calls, JSON parsing, fence stripping, error exits |
| `test_github_client.py` | Score emoji mapping, summary building, mode labels, HTML marker |
| `test_repo_config.py` | YAML loading, missing files, invalid YAML, key variants |
| `test_logger.py` | Log level mapping, GitHub Actions annotations, idempotency |

**LLM calls are mocked** — tests never hit a real API. The `unittest.mock.patch` decorator replaces `OpenAI` with a mock that returns predefined responses.

**CI workflow** (`.github/workflows/ci.yml`) runs tests on Python 3.9, 3.10, 3.11, and 3.12 on every push and PR.
