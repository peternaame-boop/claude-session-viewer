"""Tests for claude_session_viewer.services.jsonl_parser."""

from datetime import datetime
from pathlib import Path

import pytest

from claude_session_viewer.services.jsonl_parser import (
    extract_first_user_message,
    parse_session_file,
    stream_session_file,
    stream_session_from_offset,
)
from claude_session_viewer.types.messages import MessageType, TokenUsage


# ---------------------------------------------------------------------------
# 1. Parse simple session
# ---------------------------------------------------------------------------

def test_parse_simple_session(simple_session_path):
    """Parse simple_session.jsonl: 5 messages, correct types and roles."""
    messages = parse_session_file(simple_session_path)

    assert len(messages) == 5

    # Alternating user / assistant / user / assistant / user
    expected_roles = ["user", "assistant", "user", "assistant", "user"]
    expected_types = [
        MessageType.USER,
        MessageType.ASSISTANT,
        MessageType.USER,
        MessageType.ASSISTANT,
        MessageType.USER,
    ]
    for msg, role, mtype in zip(messages, expected_roles, expected_types):
        assert msg.role == role
        assert msg.type == mtype

    # First message content is a plain string
    assert messages[0].content == "Hello, can you help me with a Python script?"
    # Last message content
    assert messages[4].content == "Thanks, that looks great!"


# ---------------------------------------------------------------------------
# 2. Parse tools session
# ---------------------------------------------------------------------------

def test_parse_tools_session(tools_session_path):
    """Parse session_with_tools.jsonl: 12 messages with tool calls and results."""
    messages = parse_session_file(tools_session_path)

    assert len(messages) == 12

    # msg-t02 (assistant) should have a Read tool_call
    msg_t02 = messages[1]
    assert msg_t02.uuid == "msg-t02"
    assert len(msg_t02.tool_calls) == 1
    assert msg_t02.tool_calls[0].name == "Read"

    # msg-t03 (meta user) should have a tool_result for the Read
    msg_t03 = messages[2]
    assert msg_t03.is_meta is True
    assert len(msg_t03.tool_results) == 1
    assert msg_t03.tool_results[0].tool_use_id == "toolu_read_001"


# ---------------------------------------------------------------------------
# 3. Parse malformed session
# ---------------------------------------------------------------------------

def test_parse_malformed_session(malformed_session_path):
    """Malformed lines are skipped; only 4 valid messages returned."""
    messages = parse_session_file(malformed_session_path)

    assert len(messages) == 4

    uuids = [m.uuid for m in messages]
    assert uuids == ["msg-m01", "msg-m02", "msg-m03", "msg-m04"]


# ---------------------------------------------------------------------------
# 4. Stream equals parse
# ---------------------------------------------------------------------------

def test_stream_equals_parse(simple_session_path):
    """stream_session_file and parse_session_file produce identical results."""
    parsed = parse_session_file(simple_session_path)
    streamed = list(stream_session_file(simple_session_path))

    assert len(parsed) == len(streamed)
    for p, s in zip(parsed, streamed):
        assert p.uuid == s.uuid
        assert p.role == s.role
        assert p.type == s.type
        assert p.content == s.content


# ---------------------------------------------------------------------------
# 5. Stream from offset
# ---------------------------------------------------------------------------

def test_stream_from_offset(simple_session_path):
    """Parsing from a byte offset should yield fewer messages than full parse."""
    full = parse_session_file(simple_session_path)
    assert len(full) == 5

    # Pick an offset partway into the file (after the first line)
    file_text = simple_session_path.read_text(encoding="utf-8")
    first_newline = file_text.index("\n") + 1
    partial = list(stream_session_from_offset(simple_session_path, first_newline))

    assert len(partial) < len(full)
    assert len(partial) == 4  # skipped first line


# ---------------------------------------------------------------------------
# 6. Extract first user message
# ---------------------------------------------------------------------------

def test_extract_first_user_message(simple_session_path):
    """First user message in simple session is the greeting."""
    text = extract_first_user_message(simple_session_path)
    assert text == "Hello, can you help me with a Python script?"


# ---------------------------------------------------------------------------
# 7. Extract first user message skips meta
# ---------------------------------------------------------------------------

def test_extract_first_user_message_skips_meta(tools_session_path):
    """In tools session, meta messages are skipped; first real user is msg-t01."""
    text = extract_first_user_message(tools_session_path)
    assert text == "Read the main.py file and fix the bug on line 42."


# ---------------------------------------------------------------------------
# 8. Parse nonexistent file
# ---------------------------------------------------------------------------

def test_parse_nonexistent_file(tmp_path):
    """Parsing a file that doesn't exist returns an empty list."""
    fake_path = tmp_path / "does_not_exist.jsonl"
    messages = parse_session_file(fake_path)
    assert messages == []


# ---------------------------------------------------------------------------
# 9. Parse token usage
# ---------------------------------------------------------------------------

def test_parse_token_usage(simple_session_path):
    """Assistant messages should have TokenUsage with correct fields."""
    messages = parse_session_file(simple_session_path)

    # msg-002 (index 1) is the first assistant message
    assistant = messages[1]
    assert assistant.usage is not None
    assert isinstance(assistant.usage, TokenUsage)
    assert assistant.usage.input_tokens == 150
    assert assistant.usage.output_tokens == 25
    assert assistant.usage.cache_read_input_tokens == 100
    assert assistant.usage.cache_creation_input_tokens == 0
    assert assistant.usage.total == 275  # 150 + 25 + 100 + 0

    # msg-004 (index 3) is the second assistant
    assistant2 = messages[3]
    assert assistant2.usage is not None
    assert assistant2.usage.input_tokens == 300
    assert assistant2.usage.output_tokens == 80

    # User messages should have no usage
    assert messages[0].usage is None
    assert messages[2].usage is None


# ---------------------------------------------------------------------------
# 10. Parse timestamps
# ---------------------------------------------------------------------------

def test_parse_timestamps(simple_session_path):
    """All timestamps should be datetime objects, in chronological order."""
    messages = parse_session_file(simple_session_path)

    for msg in messages:
        assert isinstance(msg.timestamp, datetime)

    # Timestamps should be monotonically non-decreasing
    for i in range(1, len(messages)):
        assert messages[i].timestamp >= messages[i - 1].timestamp


# ---------------------------------------------------------------------------
# 11. Tool call extraction
# ---------------------------------------------------------------------------

def test_tool_call_extraction(tools_session_path):
    """Read, Edit, Bash, Grep tool calls have correct names and inputs."""
    messages = parse_session_file(tools_session_path)

    # Collect all tool calls across messages
    all_calls = []
    for msg in messages:
        all_calls.extend(msg.tool_calls)

    tool_names = [tc.name for tc in all_calls]
    assert "Read" in tool_names
    assert "Edit" in tool_names
    assert "Bash" in tool_names
    assert "Grep" in tool_names

    # Read call should have file_path input
    read_call = next(tc for tc in all_calls if tc.name == "Read")
    assert "file_path" in read_call.input
    assert read_call.input["file_path"] == "/home/wiz/projects/myapp/main.py"

    # Edit call should have old_string and new_string
    edit_call = next(tc for tc in all_calls if tc.name == "Edit")
    assert "old_string" in edit_call.input
    assert "new_string" in edit_call.input

    # Bash call should have command
    bash_call = next(tc for tc in all_calls if tc.name == "Bash")
    assert "command" in bash_call.input

    # Grep call should have pattern
    grep_call = next(tc for tc in all_calls if tc.name == "Grep")
    assert "pattern" in grep_call.input


# ---------------------------------------------------------------------------
# 12. Task tool detection
# ---------------------------------------------------------------------------

def test_task_tool_detection(subagents_session_path):
    """Task tool calls have is_task=True, task_description, task_subagent_type."""
    messages = parse_session_file(subagents_session_path)

    task_calls = []
    for msg in messages:
        for tc in msg.tool_calls:
            if tc.name == "Task":
                task_calls.append(tc)

    assert len(task_calls) == 2

    # First Task call
    assert task_calls[0].is_task is True
    assert task_calls[0].task_description == "Search API endpoints"
    assert task_calls[0].task_subagent_type == "Explore"

    # Second Task call
    assert task_calls[1].is_task is True
    assert task_calls[1].task_description == "Check security issues"
    assert task_calls[1].task_subagent_type == "general-purpose"
