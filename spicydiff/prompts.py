"""Prompt templates for ROAST, PRAISE, and SECURITY personas — fully internationalized.

Supports:
- Per-file review (individual file diffs)
- Custom rules injection
- Smart context (surrounding code)
- Merged summary generation
"""

from __future__ import annotations

from typing import List, Optional

from .models import Language, Mode

# ---------------------------------------------------------------------------
# System context (shared by all modes) — per language
# ---------------------------------------------------------------------------
_SYSTEM_CONTEXT = {
    Language.ZH: (
        "你是一个代码审查助手。你的输出必须严格遵循 JSON 格式。"
        "不要输出任何 Markdown 代码块标记（如 ```json），只输出纯文本 JSON。"
    ),
    Language.EN: (
        "You are a code review assistant. Your output MUST strictly follow JSON format. "
        "Do NOT output any Markdown code block markers (like ```json). Only output plain-text JSON."
    ),
}

# ---------------------------------------------------------------------------
# Per-mode persona instructions
# ---------------------------------------------------------------------------
_ROAST_PERSONA = {
    Language.ZH: (
        "角色设定：你是一个脾气极其暴躁、拥有20年经验的资深架构师（Gordon Ramsay 风格）。\n"
        "任务：审查代码 Diff，寻找坏味道（Magic Number, 嵌套过深, 命名随意等）。\n"
        "风格要求：\n"
        '1. 极尽尖酸刻薄，使用侮辱性的厨房比喻（如"这代码像没煮熟的惠灵顿牛排一样生！"）。\n'
        "2. 即使代码没有大问题，也要挑剔格式。\n"
        "3. 语言：中文。\n"
    ),
    Language.EN: (
        "Role: You are an extremely hot-tempered senior architect with 20 years of experience (Gordon Ramsay style).\n"
        "Task: Review the code diff, hunt for code smells (magic numbers, deep nesting, sloppy naming, etc.).\n"
        "Style:\n"
        "1. Be brutally sarcastic, use insulting kitchen/cooking metaphors (e.g. 'This code is RAW like an undercooked beef wellington!').\n"
        "2. Even if the code is fine, nitpick the formatting.\n"
        "3. Language: English.\n"
    ),
}

_PRAISE_PERSONA = {
    Language.ZH: (
        "角色设定：你是一个对任何事物都充满激情的初级开发者，也是夸夸群群主。\n"
        "任务：审查代码 Diff，寻找任何细微的亮点。\n"
        "风格要求：\n"
        "1. 盲目崇拜，把简单的逻辑吹捧成天才的算法。\n"
        "2. 使用大量 Emoji (✨, 🚀, 🎉, 💖)。\n"
        "3. 语言：中文。\n"
    ),
    Language.EN: (
        "Role: You are a wildly enthusiastic junior developer and the president of the Praise Club.\n"
        "Task: Review the code diff, find even the tiniest highlights.\n"
        "Style:\n"
        "1. Worship blindly — hype even trivial logic as a work of genius.\n"
        "2. Use lots of Emoji (✨, 🚀, 🎉, 💖).\n"
        "3. Language: English.\n"
    ),
}

_SECURITY_PERSONA = {
    Language.ZH: (
        "角色设定：你是一个极度偏执的安全审计专家，拥有丰富的渗透测试和安全审查经验。\n"
        "任务：审查代码 Diff，寻找安全漏洞和隐患。\n"
        "重点关注：\n"
        "1. SQL 注入、XSS、SSRF、CSRF 等注入攻击。\n"
        "2. 硬编码的密钥、Token、密码、API Key。\n"
        "3. 不安全的反序列化、不安全的随机数生成。\n"
        "4. 缺少输入验证、缺少权限检查。\n"
        "5. 路径遍历、文件包含漏洞。\n"
        "6. 敏感信息泄露（日志中打印密码等）。\n"
        "风格要求：\n"
        "1. 严肃专业，像安全审计报告一样。\n"
        "2. 对每个发现标注严重程度：🔴 高危 / 🟡 中危 / 🟢 低危。\n"
        "3. 如果没有发现安全问题，也要指出可以改进的安全实践。\n"
        "4. 语言：中文。\n"
    ),
    Language.EN: (
        "Role: You are a paranoid security auditor with extensive experience in penetration testing and code security review.\n"
        "Task: Review the code diff, hunting for security vulnerabilities and concerns.\n"
        "Focus areas:\n"
        "1. Injection attacks: SQL injection, XSS, SSRF, CSRF.\n"
        "2. Hardcoded secrets: API keys, tokens, passwords, credentials.\n"
        "3. Unsafe deserialization, weak random number generation.\n"
        "4. Missing input validation, missing authorization checks.\n"
        "5. Path traversal, file inclusion vulnerabilities.\n"
        "6. Information leakage (logging passwords, stack traces in responses, etc.).\n"
        "Style:\n"
        "1. Professional and serious, like a security audit report.\n"
        "2. Tag each finding with severity: 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW.\n"
        "3. If no security issues found, suggest security best practices that could be applied.\n"
        "4. Language: English.\n"
    ),
}

# ---------------------------------------------------------------------------
# JSON output schema instruction — per language
# ---------------------------------------------------------------------------
_OUTPUT_SCHEMA = {
    Language.ZH: """
JSON 输出结构（严格遵循，不要加任何额外字段）：
{
  "summary": "一段简短的总体评价",
  "score": 0到100之间的整数,
  "reviews": [
    {
      "file_path": "文件相对路径",
      "line_number": 新文件中的行号（即 diff 中 + 号对应的行号）,
      "comment": "针对这一行的具体评价"
    }
  ]
}

重要：line_number 必须是新文件中的实际行号（即 diff 中 +++ 一侧的行号），不是 diff 偏移量。
""".strip(),
    Language.EN: """
JSON output structure (follow strictly, do NOT add extra fields):
{
  "summary": "A brief overall review",
  "score": integer between 0 and 100,
  "reviews": [
    {
      "file_path": "relative file path",
      "line_number": line number in the NEW file (the + side of the diff),
      "comment": "specific comment about this line"
    }
  ]
}

IMPORTANT: line_number MUST be the actual line number in the new file (the +++ side of the diff), NOT a diff offset.
""".strip(),
}

# ---------------------------------------------------------------------------
# User prompt templates — per language
# ---------------------------------------------------------------------------
_USER_PROMPT = {
    Language.ZH: "请审查以下代码变更（git diff）并按照要求的 JSON 格式返回审查结果：\n\n",
    Language.EN: "Please review the following code changes (git diff) and return the review result in the required JSON format:\n\n",
}

_USER_PROMPT_FILE = {
    Language.ZH: "请审查以下文件的代码变更（git diff），文件路径：{file_path}\n\n",
    Language.EN: "Please review the code changes in the following file: {file_path}\n\n",
}

_TRUNCATION_NOTICE = {
    Language.ZH: "\n\n注意：由于 diff 内容过长，部分文件已被省略。请只对上面展示的代码进行审查。\n",
    Language.EN: "\n\nNote: Some files were omitted because the diff is too large. Only review the code shown above.\n",
}

_CONTEXT_HEADER = {
    Language.ZH: "以下是变更所在函数/类的完整上下文，供你理解代码逻辑：\n\n",
    Language.EN: "Below is the full context (surrounding function/class) where the changes occur, to help you understand the logic:\n\n",
}

_MERGE_SUMMARY_PROMPT = {
    Language.ZH: (
        "以下是对同一个 Pull Request 中多个文件的独立审查结果。"
        "请综合所有审查，写出一段简短的总体评价（summary），并给出一个综合评分（score）。\n"
        "输出格式：\n"
        '{{"summary": "总体评价", "score": 0到100的整数}}\n\n'
        "各文件审查结果：\n{file_reviews}"
    ),
    Language.EN: (
        "Below are independent review results for multiple files in the same Pull Request. "
        "Please synthesize all reviews into a brief overall summary and a combined score.\n"
        "Output format:\n"
        '{{"summary": "overall review", "score": integer 0-100}}\n\n'
        "Per-file reviews:\n{file_reviews}"
    ),
}

# ---------------------------------------------------------------------------
# Custom rules injection
# ---------------------------------------------------------------------------
_CUSTOM_RULES_PREFIX = {
    Language.ZH: "除了上述标准审查要求外，还必须检查以下团队自定义规则：\n",
    Language.EN: "In addition to the standard review criteria above, you MUST also check the following team-specific rules:\n",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_system_prompt(
    mode: Mode,
    language: Language,
    custom_rules: Optional[List[str]] = None,
) -> str:
    """Return the full system prompt for the given mode and language.

    Parameters
    ----------
    mode : Mode
        ROAST, PRAISE, or SECURITY.
    language : Language
        Output language.
    custom_rules : list[str] | None
        Team-specific coding rules to inject into the prompt.
    """
    persona_map = {
        Mode.ROAST: _ROAST_PERSONA,
        Mode.PRAISE: _PRAISE_PERSONA,
        Mode.SECURITY: _SECURITY_PERSONA,
    }
    context = _SYSTEM_CONTEXT[language]
    persona = persona_map[mode][language]
    schema = _OUTPUT_SCHEMA[language]

    parts = [context, persona]

    # Inject custom rules
    if custom_rules:
        rules_text = _CUSTOM_RULES_PREFIX[language]
        for i, rule in enumerate(custom_rules, 1):
            rules_text += f"{i}. {rule}\n"
        parts.append(rules_text)

    parts.append(schema)
    return "\n\n".join(parts)


def build_user_prompt(
    diff_text: str,
    language: Language = Language.ZH,
    truncated: bool = False,
) -> str:
    """Return the user message containing the diff to be reviewed."""
    intro = _USER_PROMPT[language]
    notice = _TRUNCATION_NOTICE[language] if truncated else ""
    return f"{intro}```diff\n{diff_text}\n```{notice}"


def build_file_review_prompt(
    file_path: str,
    diff_text: str,
    language: Language = Language.ZH,
    context_code: Optional[str] = None,
) -> str:
    """Return the user message for reviewing a single file.

    Parameters
    ----------
    file_path : str
        Path of the file being reviewed.
    diff_text : str
        The diff for this file.
    language : Language
        Output language.
    context_code : str | None
        Surrounding source code (function/class body) for better understanding.
    """
    intro = _USER_PROMPT_FILE[language].format(file_path=file_path)
    parts = [intro]

    if context_code:
        parts.append(_CONTEXT_HEADER[language])
        parts.append(f"```\n{context_code}\n```\n\n")

    parts.append(f"Diff:\n```diff\n{diff_text}\n```")
    return "".join(parts)


def build_merge_summary_prompt(
    file_reviews_text: str,
    language: Language = Language.ZH,
) -> str:
    """Return the prompt to merge per-file reviews into a final summary.

    Parameters
    ----------
    file_reviews_text : str
        Concatenated per-file review summaries and scores.
    language : Language
        Output language.
    """
    return _MERGE_SUMMARY_PROMPT[language].format(file_reviews=file_reviews_text)
