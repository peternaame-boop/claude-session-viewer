"""Tests for path validation and security sandboxing."""

import os
import pytest
from claude_session_viewer.utils.path_validation import (
    is_sensitive_path,
    is_path_allowed,
    validate_session_path,
    sanitize_display_path,
)


class TestIsSensitivePath:
    @pytest.mark.parametrize("path", [
        "/home/user/.ssh/id_rsa",
        "/home/user/.aws/credentials",
        "/home/user/.env",
        "/home/user/.env.local",
        "/home/user/.git-credentials",
        "/home/user/.docker/config.json",
        "/home/user/.kube/config",
        "/etc/shadow",
        "/etc/passwd",
        "/home/user/project/credentials.json",
        "/home/user/project/secrets.json",
        "/home/user/project/tokens.json",
        "/home/user/.config/gcloud/credentials",
        "/home/user/id_rsa",
        "/home/user/id_ed25519",
        "/home/user/server.key",
        "/home/user/cert.pem",
    ])
    def test_sensitive_paths_detected(self, path):
        assert is_sensitive_path(path) is True

    @pytest.mark.parametrize("path", [
        "/home/user/projects/main.py",
        "/home/user/.claude/projects/session.jsonl",
        "/home/user/documents/report.pdf",
        "/home/user/projects/envconfig.py",
        "/home/user/.local/share/app/data.db",
    ])
    def test_safe_paths_allowed(self, path):
        assert is_sensitive_path(path) is False


class TestIsPathAllowed:
    def test_claude_dir_allowed(self):
        home = os.path.expanduser("~")
        path = os.path.join(home, ".claude", "projects", "test.jsonl")
        assert is_path_allowed(path) is True

    def test_random_dir_blocked(self):
        assert is_path_allowed("/tmp/random/file.txt") is False

    def test_extra_roots(self):
        assert is_path_allowed("/tmp/test/file.txt", extra_roots=["/tmp/test"]) is True

    def test_empty_path(self):
        assert is_path_allowed("") is False


class TestValidateSessionPath:
    def test_valid_jsonl(self):
        home = os.path.expanduser("~")
        path = os.path.join(home, ".claude", "projects", "-test", "session.jsonl")
        assert validate_session_path(path) is True

    def test_non_jsonl_rejected(self):
        home = os.path.expanduser("~")
        path = os.path.join(home, ".claude", "projects", "test.txt")
        assert validate_session_path(path) is False

    def test_outside_claude_rejected(self):
        assert validate_session_path("/tmp/session.jsonl") is False


class TestSanitizeDisplayPath:
    def test_sensitive_hidden(self):
        assert sanitize_display_path("/home/user/.ssh/id_rsa") == "[sensitive path hidden]"

    def test_safe_passthrough(self):
        path = "/home/user/projects/main.py"
        assert sanitize_display_path(path) == path
