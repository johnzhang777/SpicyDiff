"""Unit tests for the prompts module."""

from spicydiff.models import Language, Mode
from spicydiff.prompts import build_system_prompt, build_user_prompt


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
        # System context should also be in English
        assert "code review assistant" in prompt

    def test_praise_zh(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.ZH)
        assert "夸夸群" in prompt
        assert "中文" in prompt

    def test_praise_en(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.EN)
        assert "Praise Club" in prompt
        assert "English" in prompt

    def test_contains_json_schema_zh(self):
        prompt = build_system_prompt(Mode.ROAST, Language.ZH)
        assert "summary" in prompt
        assert "score" in prompt
        assert "reviews" in prompt

    def test_contains_json_schema_en(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        assert "summary" in prompt
        assert "score" in prompt
        assert "reviews" in prompt
        assert "line_number" in prompt

    def test_en_system_context_is_english(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        # Should NOT contain Chinese system context
        assert "你是一个代码审查助手" not in prompt

    def test_zh_system_context_is_chinese(self):
        prompt = build_system_prompt(Mode.ROAST, Language.ZH)
        assert "你是一个代码审查助手" in prompt

    def test_en_schema_is_english(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.EN)
        assert "A brief overall review" in prompt

    def test_line_number_clarification_en(self):
        prompt = build_system_prompt(Mode.ROAST, Language.EN)
        assert "new file" in prompt.lower() or "NEW file" in prompt


class TestBuildUserPrompt:
    def test_includes_diff_zh(self):
        diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        prompt = build_user_prompt(diff, Language.ZH)
        assert "```diff" in prompt
        assert diff in prompt

    def test_includes_diff_en(self):
        diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        prompt = build_user_prompt(diff, Language.EN)
        assert "```diff" in prompt
        assert diff in prompt
        assert "Please review" in prompt

    def test_en_prompt_is_english(self):
        prompt = build_user_prompt("diff text", Language.EN)
        assert "请审查" not in prompt

    def test_zh_prompt_is_chinese(self):
        prompt = build_user_prompt("diff text", Language.ZH)
        assert "请审查" in prompt

    def test_truncation_notice_zh(self):
        prompt = build_user_prompt("diff", Language.ZH, truncated=True)
        assert "省略" in prompt

    def test_truncation_notice_en(self):
        prompt = build_user_prompt("diff", Language.EN, truncated=True)
        assert "omitted" in prompt

    def test_no_truncation_notice(self):
        prompt = build_user_prompt("diff", Language.EN, truncated=False)
        assert "omitted" not in prompt
