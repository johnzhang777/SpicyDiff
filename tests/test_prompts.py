"""Unit tests for the prompts module."""

from spicydiff.models import Language, Mode
from spicydiff.prompts import (
    build_system_prompt,
    build_user_prompt,
    build_file_review_prompt,
    build_merge_summary_prompt,
)


class TestBuildSystemPrompt:
    def test_roast_zh(self):
        prompt = build_system_prompt(Mode.ROAST, Language.ZH)
        assert "Gordon Ramsay" in prompt
        assert "中文" in prompt
        assert "JSON" in prompt

    def test_roast_en(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        assert "Gordon Ramsay" in prompt
        assert "English" in prompt
        assert "code review assistant" in prompt

    def test_praise_zh(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.ZH)
        assert "夸夸群" in prompt

    def test_praise_en(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.EN)
        assert "Praise Club" in prompt

    def test_security_zh(self):
        prompt = build_system_prompt(Mode.SECURITY, Language.ZH)
        assert "安全" in prompt
        assert "SQL" in prompt
        assert "高危" in prompt

    def test_security_en(self):
        prompt = build_system_prompt(Mode.SECURITY, Language.EN)
        assert "security" in prompt.lower()
        assert "SQL injection" in prompt
        assert "HIGH" in prompt

    def test_contains_json_schema_zh(self):
        prompt = build_system_prompt(Mode.ROAST, Language.ZH)
        assert "summary" in prompt
        assert "score" in prompt

    def test_contains_json_schema_en(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        assert "summary" in prompt
        assert "line_number" in prompt

    def test_en_system_context_is_english(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        assert "你是一个代码审查助手" not in prompt

    def test_zh_system_context_is_chinese(self):
        prompt = build_system_prompt(Mode.ROAST, Language.ZH)
        assert "你是一个代码审查助手" in prompt

    def test_custom_rules_zh(self):
        rules = ["所有函数必须有文档注释", "禁止硬编码 URL"]
        prompt = build_system_prompt(Mode.ROAST, Language.ZH, custom_rules=rules)
        assert "团队自定义规则" in prompt
        assert "所有函数必须有文档注释" in prompt
        assert "禁止硬编码 URL" in prompt

    def test_custom_rules_en(self):
        rules = ["All functions must have docstrings", "No hardcoded URLs"]
        prompt = build_system_prompt(Mode.ROAST, Language.EN, custom_rules=rules)
        assert "team-specific rules" in prompt
        assert "All functions must have docstrings" in prompt
        assert "No hardcoded URLs" in prompt

    def test_no_custom_rules(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        assert "team-specific rules" not in prompt

    def test_empty_custom_rules(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN, custom_rules=[])
        assert "team-specific rules" not in prompt


class TestBuildUserPrompt:
    def test_includes_diff_zh(self):
        diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        prompt = build_user_prompt(diff, Language.ZH)
        assert "```diff" in prompt
        assert diff in prompt

    def test_includes_diff_en(self):
        diff = "some diff"
        prompt = build_user_prompt(diff, Language.EN)
        assert "Please review" in prompt

    def test_truncation_notice_zh(self):
        prompt = build_user_prompt("diff", Language.ZH, truncated=True)
        assert "省略" in prompt

    def test_truncation_notice_en(self):
        prompt = build_user_prompt("diff", Language.EN, truncated=True)
        assert "omitted" in prompt


class TestBuildFileReviewPrompt:
    def test_basic(self):
        prompt = build_file_review_prompt("src/main.py", "diff text", Language.EN)
        assert "src/main.py" in prompt
        assert "diff text" in prompt

    def test_with_context(self):
        prompt = build_file_review_prompt(
            "app.py", "diff", Language.EN, context_code="def foo():\n    pass"
        )
        assert "context" in prompt.lower()
        assert "def foo():" in prompt

    def test_no_context(self):
        prompt = build_file_review_prompt("app.py", "diff", Language.EN)
        assert "context" not in prompt.lower()

    def test_zh(self):
        prompt = build_file_review_prompt("main.go", "diff", Language.ZH)
        assert "main.go" in prompt


class TestBuildMergeSummaryPrompt:
    def test_en(self):
        reviews = "- file1.py (score: 30): Bad code"
        prompt = build_merge_summary_prompt(reviews, Language.EN)
        assert "file1.py" in prompt
        assert "summary" in prompt

    def test_zh(self):
        reviews = "- file1.py (score: 30): 糟糕的代码"
        prompt = build_merge_summary_prompt(reviews, Language.ZH)
        assert "file1.py" in prompt
        assert "总体评价" in prompt
