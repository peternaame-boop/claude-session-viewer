"""Tests for content sanitization."""

import pytest
from claude_session_viewer.utils.content_sanitizer import (
    sanitize_content,
    extract_user_text,
    extract_thinking_text,
    extract_slash_commands,
    extract_file_references,
)


class TestSanitizeContent:
    def test_strips_system_reminder(self):
        text = "Hello <system-reminder>secret stuff</system-reminder> world"
        assert sanitize_content(text) == "Hello  world"

    def test_strips_teammate_message(self):
        text = 'Before <teammate-message summary="test">content</teammate-message> After'
        assert sanitize_content(text) == "Before  After"

    def test_strips_local_command(self):
        text = "Hello <local-command-caveat>warning</local-command-caveat> there"
        assert sanitize_content(text) == "Hello  there"

    def test_strips_command_tags(self):
        text = "<command-name>/compact</command-name><command-message>msg</command-message>"
        assert sanitize_content(text) == ""

    def test_preserves_clean_text(self):
        text = "This is perfectly normal text."
        assert sanitize_content(text) == "This is perfectly normal text."

    def test_empty_string(self):
        assert sanitize_content("") == ""

    def test_none_returns_empty(self):
        assert sanitize_content(None) == ""

    def test_multiline_removal(self):
        text = "Start\n<system-reminder>\nmulti\nline\n</system-reminder>\nEnd"
        result = sanitize_content(text)
        assert "<system-reminder>" not in result
        assert "End" in result


class TestExtractUserText:
    def test_string_content(self):
        assert extract_user_text("Hello world") == "Hello world"

    def test_list_content(self):
        content = [{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}]
        assert extract_user_text(content) == "Hello\nWorld"

    def test_mixed_content_blocks(self):
        content = [{"type": "text", "text": "Hello"}, {"type": "tool_result", "content": "ignored"}]
        assert extract_user_text(content) == "Hello"

    def test_empty_content(self):
        assert extract_user_text("") == ""
        assert extract_user_text([]) == ""


class TestExtractThinkingText:
    def test_extracts_thinking(self):
        content = [
            {"type": "thinking", "thinking": "Let me think..."},
            {"type": "text", "text": "Here's my answer"},
        ]
        assert extract_thinking_text(content) == "Let me think..."

    def test_multiple_thinking_blocks(self):
        content = [
            {"type": "thinking", "thinking": "First thought"},
            {"type": "text", "text": "response"},
            {"type": "thinking", "thinking": "Second thought"},
        ]
        assert "First thought" in extract_thinking_text(content)
        assert "Second thought" in extract_thinking_text(content)

    def test_no_thinking(self):
        content = [{"type": "text", "text": "Just text"}]
        assert extract_thinking_text(content) == ""

    def test_string_content(self):
        assert extract_thinking_text("just a string") == ""


class TestExtractSlashCommands:
    def test_finds_commands(self):
        text = "Please /compact the context and then /review"
        cmds = extract_slash_commands(text)
        assert "/compact" in cmds
        assert "/review" in cmds

    def test_command_at_start(self):
        cmds = extract_slash_commands("/help me")
        assert "/help" in cmds

    def test_no_commands(self):
        assert extract_slash_commands("No commands here") == []

    def test_url_not_command(self):
        # URLs shouldn't match as commands (they have :// before /)
        cmds = extract_slash_commands("Visit https://example.com/page")
        assert "/page" not in cmds or len(cmds) == 0


class TestExtractFileReferences:
    def test_absolute_path(self):
        refs = extract_file_references("Check @/home/wiz/main.py for bugs")
        assert "/home/wiz/main.py" in refs

    def test_relative_path(self):
        refs = extract_file_references("Look at @./src/app.py")
        assert "./src/app.py" in refs

    def test_filename_with_extension(self):
        refs = extract_file_references("See @main.py and @test.ts")
        assert "main.py" in refs
        assert "test.ts" in refs

    def test_no_references(self):
        assert extract_file_references("No file refs here") == []
