"""Tests for claude_session_viewer.utils.diff_generator."""

import pytest

from claude_session_viewer.utils.diff_generator import (
    compute_unified_diff,
    compute_inline_diff,
    get_file_extension,
    get_syntax_definition,
    strip_line_numbers,
)


class TestComputeUnifiedDiff:
    def test_simple_change(self):
        old = "hello\nworld\n"
        new = "hello\nearth\n"
        diff = compute_unified_diff(old, new, "test.txt")
        assert "-world" in diff
        assert "+earth" in diff

    def test_empty_strings(self):
        diff = compute_unified_diff("", "")
        assert diff == ""

    def test_identical_strings(self):
        text = "same\ncontent\n"
        diff = compute_unified_diff(text, text)
        assert diff == ""

    def test_file_path_in_header(self):
        diff = compute_unified_diff("a\n", "b\n", "/home/user/main.py")
        assert "main.py" in diff


class TestComputeInlineDiff:
    def test_simple_replacement(self):
        lines = compute_inline_diff("old line", "new line")
        types = [l["type"] for l in lines]
        assert "removed" in types
        assert "added" in types

    def test_addition(self):
        lines = compute_inline_diff("line1", "line1\nline2")
        added = [l for l in lines if l["type"] == "added"]
        assert len(added) >= 1

    def test_deletion(self):
        lines = compute_inline_diff("line1\nline2", "line1")
        removed = [l for l in lines if l["type"] == "removed"]
        assert len(removed) >= 1

    def test_equal_content(self):
        lines = compute_inline_diff("same", "same")
        assert all(l["type"] == "context" for l in lines)

    def test_empty_inputs(self):
        lines = compute_inline_diff("", "")
        assert lines == []

    def test_line_prefixes(self):
        lines = compute_inline_diff("old", "new")
        for l in lines:
            if l["type"] == "removed":
                assert l["text"].startswith("-")
            elif l["type"] == "added":
                assert l["text"].startswith("+")
            elif l["type"] == "context":
                assert l["text"].startswith(" ")


class TestGetFileExtension:
    def test_python(self):
        assert get_file_extension("/home/user/main.py") == "py"

    def test_javascript(self):
        assert get_file_extension("app.js") == "js"

    def test_no_extension(self):
        assert get_file_extension("Makefile") == ""

    def test_empty_path(self):
        assert get_file_extension("") == ""

    def test_dotfile(self):
        assert get_file_extension(".gitignore") == "gitignore"

    def test_multiple_dots(self):
        assert get_file_extension("archive.tar.gz") == "gz"


class TestGetSyntaxDefinition:
    def test_python(self):
        assert get_syntax_definition("main.py") == "Python"

    def test_javascript(self):
        assert get_syntax_definition("app.js") == "JavaScript"

    def test_typescript(self):
        assert get_syntax_definition("app.ts") == "TypeScript"

    def test_rust(self):
        assert get_syntax_definition("lib.rs") == "Rust"

    def test_unknown_extension(self):
        assert get_syntax_definition("file.xyz") == ""

    def test_makefile_by_name(self):
        assert get_syntax_definition("Makefile") == "Makefile"

    def test_dockerfile_by_name(self):
        assert get_syntax_definition("Dockerfile") == "Dockerfile"

    def test_empty_path(self):
        assert get_syntax_definition("") == ""

    def test_bash(self):
        assert get_syntax_definition("script.sh") == "Bash"

    def test_qml(self):
        assert get_syntax_definition("Main.qml") == "QML"


class TestStripLineNumbers:
    def test_cat_n_tab_format(self):
        text = "     1\timport foo\n     2\timport bar\n     3\t"
        result = strip_line_numbers(text)
        assert result == "import foo\nimport bar\n"

    def test_cat_n_arrow_format(self):
        text = '     1\u2192"""Module doc."""\n     2\u2192\n     3\u2192import os'
        result = strip_line_numbers(text)
        assert result == '"""Module doc."""\n\nimport os'

    def test_no_line_numbers(self):
        text = "just plain text\nno numbers here"
        assert strip_line_numbers(text) == text

    def test_empty_string(self):
        assert strip_line_numbers("") == ""

    def test_preserves_empty_lines(self):
        text = "     1\u2192code\n\n     3\u2192more code"
        result = strip_line_numbers(text)
        assert result == "code\n\nmore code"

    def test_high_line_numbers(self):
        text = "   100\u2192line hundred\n   101\u2192line hundred one"
        result = strip_line_numbers(text)
        assert result == "line hundred\nline hundred one"

    def test_mixed_format_not_stripped(self):
        # If it doesn't look like cat -n, leave it alone
        text = "1. First item\n2. Second item"
        assert strip_line_numbers(text) == text
