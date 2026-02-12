"""Unit tests for the repo_config module."""

import os
import tempfile

from spicydiff.repo_config import load_repo_config, RepoConfig


class TestLoadRepoConfig:
    def test_no_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = load_repo_config(tmpdir)
            assert isinstance(cfg, RepoConfig)
            assert cfg.custom_rules == []
            assert cfg.exclude == []
            assert cfg.mode is None
            assert not cfg.has_overrides

    def test_loads_spicydiff_yml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, ".spicydiff.yml")
            with open(config_path, "w") as f:
                f.write(
                    "mode: ROAST\n"
                    "language: zh\n"
                    "rules:\n"
                    "  - No magic numbers\n"
                    "  - All functions must have docstrings\n"
                    "exclude:\n"
                    "  - '*.test.js'\n"
                    "  - 'docs/**'\n"
                    "temperature: 0.5\n"
                )
            cfg = load_repo_config(tmpdir)
            assert cfg.mode == "ROAST"
            assert cfg.language == "zh"
            assert len(cfg.custom_rules) == 2
            assert "No magic numbers" in cfg.custom_rules
            assert len(cfg.exclude) == 2
            assert cfg.temperature == 0.5
            assert cfg.has_overrides

    def test_loads_yaml_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, ".spicydiff.yaml")
            with open(config_path, "w") as f:
                f.write("mode: PRAISE\n")
            cfg = load_repo_config(tmpdir)
            assert cfg.mode == "PRAISE"

    def test_loads_without_dot_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "spicydiff.yml")
            with open(config_path, "w") as f:
                f.write("language: en\n")
            cfg = load_repo_config(tmpdir)
            assert cfg.language == "en"

    def test_custom_rules_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, ".spicydiff.yml")
            with open(config_path, "w") as f:
                f.write("custom_rules:\n  - Rule A\n  - Rule B\n")
            cfg = load_repo_config(tmpdir)
            assert cfg.custom_rules == ["Rule A", "Rule B"]

    def test_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, ".spicydiff.yml")
            with open(config_path, "w") as f:
                f.write("!!not valid yaml: [[[")
            cfg = load_repo_config(tmpdir)
            # Should not crash, just return empty
            assert isinstance(cfg, RepoConfig)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, ".spicydiff.yml")
            with open(config_path, "w") as f:
                f.write("")
            cfg = load_repo_config(tmpdir)
            assert isinstance(cfg, RepoConfig)
            assert not cfg.has_overrides

    def test_max_tokens_hyphenated_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, ".spicydiff.yml")
            with open(config_path, "w") as f:
                f.write("max-tokens: 2048\nmax-diff-chars: 30000\n")
            cfg = load_repo_config(tmpdir)
            assert cfg.max_tokens == 2048
            assert cfg.max_diff_chars == 30000


class TestRepoConfigHasOverrides:
    def test_empty(self):
        assert not RepoConfig().has_overrides

    def test_with_mode(self):
        assert RepoConfig(mode="ROAST").has_overrides

    def test_with_rules(self):
        assert RepoConfig(custom_rules=["rule1"]).has_overrides
