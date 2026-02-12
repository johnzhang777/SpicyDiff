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

    def test_praise_zh(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.ZH)
        assert "夸夸群" in prompt
        assert "中文" in prompt

    def test_praise_en(self):
        prompt = build_system_prompt(Mode.PRAISE, Language.EN)
        assert "Praise Club" in prompt
        assert "English" in prompt

    def test_contains_json_schema(self):
        prompt = build_system_prompt(Mode.ROAST, Language.ZH)
        assert "summary" in prompt
        assert "score" in prompt
        assert "reviews" in prompt


class TestBuildUserPrompt:
    def test_includes_diff(self):
        diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new"
        prompt = build_user_prompt(diff)
        assert "```diff" in prompt
        assert diff in prompt
