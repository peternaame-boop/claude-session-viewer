"""Tests for claude_session_viewer.services.context_analyzer."""

import pytest
from datetime import datetime

from claude_session_viewer.services.context_analyzer import analyze_context
from claude_session_viewer.types.chunks import Chunk, ChunkType
from claude_session_viewer.types.context import ContextCategory
from claude_session_viewer.types.messages import (
    MessageType,
    ParsedMessage,
    ToolCall,
    ToolResult,
    TokenUsage,
)
from claude_session_viewer.types.sessions import SessionMetrics


# ---------------------------------------------------------------------------
# Helpers for building test data
# ---------------------------------------------------------------------------

_TS = datetime(2026, 2, 14, 12, 0, 0)
_EMPTY_METRICS = SessionMetrics()


def _user_chunk(text: str = "hello", *, chunk_id: str = "u1") -> Chunk:
    msg = ParsedMessage(
        uuid="msg-u",
        parent_uuid=None,
        type=MessageType.USER,
        timestamp=_TS,
        role="user",
        content=text,
    )
    return Chunk(
        id=chunk_id,
        chunk_type=ChunkType.USER,
        start_time=_TS,
        end_time=_TS,
        metrics=_EMPTY_METRICS,
        messages=[msg],
        user_text=text,
    )


def _ai_chunk(
    *,
    tool_calls: list[ToolCall] | None = None,
    tool_results: list[ToolResult] | None = None,
    content=None,
    role: str = "assistant",
    chunk_id: str = "a1",
) -> Chunk:
    """Build an AI chunk with one assistant message."""
    msg = ParsedMessage(
        uuid="msg-a",
        parent_uuid=None,
        type=MessageType.ASSISTANT,
        timestamp=_TS,
        role=role,
        content=content or "I'll help with that.",
        tool_calls=tool_calls or [],
        tool_results=tool_results or [],
    )
    # If there are tool results on a separate meta message, add it
    messages = [msg]

    # Also add a meta-user message for tool results if the main msg has tool_calls
    # but results are on a separate message (common pattern)
    if tool_calls and tool_results:
        meta_msg = ParsedMessage(
            uuid="msg-meta",
            parent_uuid=None,
            type=MessageType.USER,
            timestamp=_TS,
            role="user",
            content="",
            is_meta=True,
            tool_results=tool_results,
        )
        # Put results on the meta message, not the assistant message
        msg.tool_results = []
        messages.append(meta_msg)

    return Chunk(
        id=chunk_id,
        chunk_type=ChunkType.AI,
        start_time=_TS,
        end_time=_TS,
        metrics=_EMPTY_METRICS,
        messages=messages,
    )


def _ai_chunk_with_results_on_same_msg(
    *,
    tool_calls: list[ToolCall] | None = None,
    tool_results: list[ToolResult] | None = None,
    content=None,
    chunk_id: str = "a1",
) -> Chunk:
    """Build an AI chunk where tool calls and results live on the same message."""
    msg = ParsedMessage(
        uuid="msg-a",
        parent_uuid=None,
        type=MessageType.ASSISTANT,
        timestamp=_TS,
        role="assistant",
        content=content or "Response text",
        tool_calls=tool_calls or [],
        tool_results=tool_results or [],
    )
    return Chunk(
        id=chunk_id,
        chunk_type=ChunkType.AI,
        start_time=_TS,
        end_time=_TS,
        metrics=_EMPTY_METRICS,
        messages=[msg],
    )


def _compact_chunk(summary_text: str = "Summary of conversation so far.") -> Chunk:
    msg = ParsedMessage(
        uuid="msg-c",
        parent_uuid=None,
        type=MessageType.SUMMARY,
        timestamp=_TS,
        role="assistant",
        content=summary_text,
        is_compact_summary=True,
    )
    return Chunk(
        id="compact-1",
        chunk_type=ChunkType.COMPACT,
        start_time=_TS,
        end_time=_TS,
        metrics=_EMPTY_METRICS,
        messages=[msg],
    )


# ---------------------------------------------------------------------------
# Tests: empty / minimal inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_empty_list(self):
        result = analyze_context([])
        assert result == []

    def test_single_user_chunk(self):
        chunks = [_user_chunk("hi there")]
        result = analyze_context(chunks)
        assert len(result) == 1
        assert result[0].phase_number == 1
        # Should have a user-message injection
        cats = [inj.category for inj in result[0].new_injections]
        assert ContextCategory.USER_MESSAGE in cats

    def test_single_ai_chunk_no_tools(self):
        chunk = _ai_chunk(content="Just text response")
        chunks = [chunk]
        result = analyze_context(chunks)
        assert len(result) == 1
        # No tool calls -> no tool-output injections
        tool_injs = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TOOL_OUTPUT
        ]
        assert len(tool_injs) == 0


# ---------------------------------------------------------------------------
# Tests: claude-md detection
# ---------------------------------------------------------------------------


class TestClaudeMdDetection:
    def test_read_claude_md_file(self):
        tc = ToolCall(id="tc1", name="Read", input={"file_path": "/home/user/project/CLAUDE.md"})
        tr = ToolResult(tool_use_id="tc1", content="# Project rules\nDo this and that.")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        claude_md = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.CLAUDE_MD
        ]
        assert len(claude_md) == 1
        assert claude_md[0].path == "/home/user/project/CLAUDE.md"
        assert claude_md[0].estimated_tokens > 0

    def test_read_claude_settings_json(self):
        tc = ToolCall(id="tc1", name="Read", input={"file_path": "/home/user/.claude/settings.json"})
        tr = ToolResult(tool_use_id="tc1", content='{"key": "value"}')
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        claude_md = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.CLAUDE_MD
        ]
        assert len(claude_md) == 1

    def test_system_reminder_in_content(self):
        content = [
            {"type": "text", "text": "<system-reminder>You are helpful</system-reminder>"}
        ]
        msg = ParsedMessage(
            uuid="msg-sys",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            timestamp=_TS,
            role="assistant",
            content=content,
        )
        chunk = Chunk(
            id="a-sys",
            chunk_type=ChunkType.AI,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg],
        )
        result = analyze_context([chunk])

        claude_md = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.CLAUDE_MD
        ]
        assert len(claude_md) == 1
        assert claude_md[0].display_name == "System reminder"

    def test_system_reminder_in_string_content(self):
        msg = ParsedMessage(
            uuid="msg-sys",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            timestamp=_TS,
            role="assistant",
            content="Some text with <system-reminder>config</system-reminder>",
        )
        chunk = Chunk(
            id="a-sys",
            chunk_type=ChunkType.AI,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg],
        )
        result = analyze_context([chunk])
        claude_md = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.CLAUDE_MD
        ]
        assert len(claude_md) == 1

    def test_non_claude_md_read_not_detected(self):
        tc = ToolCall(id="tc1", name="Read", input={"file_path": "/home/user/main.py"})
        tr = ToolResult(tool_use_id="tc1", content="import os")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        claude_md = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.CLAUDE_MD
        ]
        assert len(claude_md) == 0


# ---------------------------------------------------------------------------
# Tests: mentioned-file detection
# ---------------------------------------------------------------------------


class TestMentionedFileDetection:
    def test_at_mention_in_user_text(self):
        user = _user_chunk("Please look at @src/main.py")
        tc = ToolCall(id="tc1", name="Read", input={"file_path": "/home/user/src/main.py"})
        tr = ToolResult(tool_use_id="tc1", content="import os\nimport sys\n" * 10)
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr], chunk_id="a1")
        result = analyze_context([user, ai])

        mentioned = [
            inj for inj in result[1].new_injections
            if inj.category == ContextCategory.MENTIONED_FILE
        ]
        assert len(mentioned) == 1
        assert "main.py" in mentioned[0].display_name

    def test_multiple_at_mentions(self):
        user = _user_chunk("Check @foo.py and @bar.js")
        ai = _ai_chunk(chunk_id="a1")
        result = analyze_context([user, ai])

        mentioned = [
            inj for inj in result[1].new_injections
            if inj.category == ContextCategory.MENTIONED_FILE
        ]
        assert len(mentioned) == 2

    def test_no_mentions(self):
        user = _user_chunk("Just a normal message")
        ai = _ai_chunk(chunk_id="a1")
        result = analyze_context([user, ai])

        mentioned = [
            inj for inj in result[1].new_injections
            if inj.category == ContextCategory.MENTIONED_FILE
        ]
        assert len(mentioned) == 0

    def test_no_preceding_user_chunk(self):
        ai = _ai_chunk(chunk_id="a1")
        result = analyze_context([ai])

        mentioned = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.MENTIONED_FILE
        ]
        assert len(mentioned) == 0


# ---------------------------------------------------------------------------
# Tests: tool-output detection
# ---------------------------------------------------------------------------


class TestToolOutputDetection:
    def test_single_tool_call(self):
        tc = ToolCall(id="tc1", name="Bash", input={"command": "ls -la"})
        tr = ToolResult(tool_use_id="tc1", content="file1.txt\nfile2.txt\n")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        tool_out = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TOOL_OUTPUT
        ]
        assert len(tool_out) == 1
        assert tool_out[0].display_name == "Bash"
        assert tool_out[0].estimated_tokens > 0
        assert len(tool_out[0].tool_breakdown) == 2

    def test_multiple_tool_calls(self):
        tc1 = ToolCall(id="tc1", name="Bash", input={"command": "ls"})
        tc2 = ToolCall(id="tc2", name="Grep", input={"pattern": "foo"})
        tr1 = ToolResult(tool_use_id="tc1", content="output1")
        tr2 = ToolResult(tool_use_id="tc2", content="output2")
        chunk = _ai_chunk(tool_calls=[tc1, tc2], tool_results=[tr1, tr2])
        result = analyze_context([chunk])

        tool_out = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TOOL_OUTPUT
        ]
        assert len(tool_out) == 2

    def test_task_tools_excluded_from_tool_output(self):
        tc = ToolCall(id="tc1", name="Task", input={"description": "do something"})
        tr = ToolResult(tool_use_id="tc1", content="task done")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        tool_out = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TOOL_OUTPUT
        ]
        assert len(tool_out) == 0

    def test_claude_md_read_excluded_from_tool_output(self):
        tc = ToolCall(id="tc1", name="Read", input={"file_path": "/project/CLAUDE.md"})
        tr = ToolResult(tool_use_id="tc1", content="rules here")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        tool_out = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TOOL_OUTPUT
        ]
        assert len(tool_out) == 0

    def test_tool_breakdown_structure(self):
        tc = ToolCall(id="tc1", name="Bash", input={"command": "echo hello"})
        tr = ToolResult(tool_use_id="tc1", content="hello\n")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        tool_out = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TOOL_OUTPUT
        ]
        assert len(tool_out) == 1
        bd = tool_out[0].tool_breakdown
        assert any(d["label"] == "input" for d in bd)
        assert any(d["label"] == "output" for d in bd)


# ---------------------------------------------------------------------------
# Tests: thinking-text detection
# ---------------------------------------------------------------------------


class TestThinkingTextDetection:
    def test_thinking_block_detected(self):
        content = [
            {"type": "thinking", "thinking": "Let me reason about this step by step..."},
            {"type": "text", "text": "Here is my answer."},
        ]
        msg = ParsedMessage(
            uuid="msg-think",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            timestamp=_TS,
            role="assistant",
            content=content,
        )
        chunk = Chunk(
            id="a-think",
            chunk_type=ChunkType.AI,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg],
        )
        result = analyze_context([chunk])

        thinking = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.THINKING_TEXT
        ]
        assert len(thinking) == 1
        assert thinking[0].display_name == "Extended thinking"
        assert thinking[0].estimated_tokens > 0

    def test_no_thinking_blocks(self):
        content = [{"type": "text", "text": "Just a normal response."}]
        msg = ParsedMessage(
            uuid="msg-plain",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            timestamp=_TS,
            role="assistant",
            content=content,
        )
        chunk = Chunk(
            id="a-plain",
            chunk_type=ChunkType.AI,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg],
        )
        result = analyze_context([chunk])

        thinking = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.THINKING_TEXT
        ]
        assert len(thinking) == 0

    def test_thinking_on_non_assistant_ignored(self):
        """Thinking blocks on non-assistant messages should be ignored."""
        content = [{"type": "thinking", "thinking": "some thinking"}]
        msg = ParsedMessage(
            uuid="msg-u-think",
            parent_uuid=None,
            type=MessageType.USER,
            timestamp=_TS,
            role="user",
            content=content,
        )
        chunk = Chunk(
            id="a-u-think",
            chunk_type=ChunkType.AI,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg],
        )
        result = analyze_context([chunk])

        thinking = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.THINKING_TEXT
        ]
        assert len(thinking) == 0


# ---------------------------------------------------------------------------
# Tests: task-coordination detection
# ---------------------------------------------------------------------------


class TestTaskCoordinationDetection:
    def test_task_tool_detected(self):
        tc = ToolCall(id="tc1", name="Task", input={"description": "analyze code"})
        tr = ToolResult(tool_use_id="tc1", content="Analysis complete: found 3 issues")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        task = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TASK_COORDINATION
        ]
        assert len(task) == 1
        assert task[0].display_name == "Task"

    def test_skill_tool_detected(self):
        tc = ToolCall(id="tc1", name="Skill", input={"skill": "commit"})
        tr = ToolResult(tool_use_id="tc1", content="committed")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        task = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TASK_COORDINATION
        ]
        assert len(task) == 1
        assert task[0].display_name == "Skill"

    def test_all_task_tool_names(self):
        task_names = ["Task", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "TaskOutput", "Skill"]
        for name in task_names:
            tc = ToolCall(id=f"tc-{name}", name=name, input={"x": "y"})
            tr = ToolResult(tool_use_id=f"tc-{name}", content="done")
            chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
            result = analyze_context([chunk])

            task = [
                inj for inj in result[0].new_injections
                if inj.category == ContextCategory.TASK_COORDINATION
            ]
            assert len(task) == 1, f"Expected task injection for {name}"

    def test_non_task_tool_not_detected(self):
        tc = ToolCall(id="tc1", name="Bash", input={"command": "ls"})
        tr = ToolResult(tool_use_id="tc1", content="output")
        chunk = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        result = analyze_context([chunk])

        task = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.TASK_COORDINATION
        ]
        assert len(task) == 0


# ---------------------------------------------------------------------------
# Tests: user-message detection
# ---------------------------------------------------------------------------


class TestUserMessageDetection:
    def test_user_text_creates_injection(self):
        user = _user_chunk("Please help me with this code")
        result = analyze_context([user])

        user_injs = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.USER_MESSAGE
        ]
        assert len(user_injs) == 1
        assert user_injs[0].estimated_tokens > 0

    def test_empty_user_text_no_injection(self):
        user = _user_chunk("")
        result = analyze_context([user])

        user_injs = [
            inj for inj in result[0].new_injections
            if inj.category == ContextCategory.USER_MESSAGE
        ]
        assert len(user_injs) == 0


# ---------------------------------------------------------------------------
# Tests: phase tracking across compactions
# ---------------------------------------------------------------------------


class TestPhaseTracking:
    def test_single_phase_no_compaction(self):
        chunks = [_user_chunk("hi"), _ai_chunk()]
        result = analyze_context(chunks)
        assert all(s.phase_number == 1 for s in result)

    def test_compaction_increments_phase(self):
        chunks = [
            _user_chunk("hi"),
            _ai_chunk(),
            _compact_chunk("Summary of phase 1"),
            _user_chunk("continue", chunk_id="u2"),
            _ai_chunk(chunk_id="a2"),
        ]
        result = analyze_context(chunks)

        assert result[0].phase_number == 1  # user
        assert result[1].phase_number == 1  # ai
        assert result[2].phase_number == 1  # compact (still in phase 1)
        assert result[3].phase_number == 2  # user after compaction
        assert result[4].phase_number == 2  # ai after compaction

    def test_multiple_compactions(self):
        chunks = [
            _user_chunk("phase 1"),
            _ai_chunk(),
            _compact_chunk("summary 1"),
            _user_chunk("phase 2", chunk_id="u2"),
            _ai_chunk(chunk_id="a2"),
            _compact_chunk("summary 2"),
            _user_chunk("phase 3", chunk_id="u3"),
        ]
        result = analyze_context(chunks)

        assert result[0].phase_number == 1
        assert result[2].phase_number == 1  # compact chunk
        assert result[3].phase_number == 2
        assert result[5].phase_number == 2  # second compact chunk
        assert result[6].phase_number == 3

    def test_compaction_tokens_freed(self):
        """After compaction, the compact chunk should track tokens freed."""
        user = _user_chunk("a" * 400)  # ~100 tokens
        tc = ToolCall(id="tc1", name="Bash", input={"command": "ls"})
        tr = ToolResult(tool_use_id="tc1", content="b" * 800)  # ~200 tokens
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])
        compact = _compact_chunk("short")  # small summary

        chunks = [user, ai, compact]
        result = analyze_context(chunks)

        # The compact chunk should have recorded tokens_freed on the chunk
        assert chunks[2].tokens_freed >= 0

    def test_accumulated_injections_reset_after_compaction(self):
        user1 = _user_chunk("first message")
        ai1 = _ai_chunk()
        compact = _compact_chunk("summary")
        user2 = _user_chunk("second message", chunk_id="u2")
        ai2 = _ai_chunk(chunk_id="a2")

        chunks = [user1, ai1, compact, user2, ai2]
        result = analyze_context(chunks)

        # Before compaction, accumulated should include user1 + ai1 injections
        assert len(result[1].accumulated_injections) >= 1

        # After compaction, user2 starts fresh accumulation
        # user2 has its own injection, ai2 adds more
        post_compact_accumulated = result[4].accumulated_injections
        # These should only contain injections from phase 2
        pre_compact_ids = {inj.id for inj in result[1].accumulated_injections}
        post_compact_ids = {inj.id for inj in post_compact_accumulated}
        assert pre_compact_ids.isdisjoint(post_compact_ids)


# ---------------------------------------------------------------------------
# Tests: accumulated injection tracking
# ---------------------------------------------------------------------------


class TestAccumulatedInjections:
    def test_injections_accumulate_across_chunks(self):
        user = _user_chunk("hello")
        tc = ToolCall(id="tc1", name="Bash", input={"command": "ls"})
        tr = ToolResult(tool_use_id="tc1", content="output")
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])

        chunks = [user, ai]
        result = analyze_context(chunks)

        # AI chunk should have accumulated injections from both user and AI
        assert len(result[1].accumulated_injections) > len(result[0].accumulated_injections)

    def test_total_estimated_tokens_grows(self):
        user = _user_chunk("some user text here")
        tc = ToolCall(id="tc1", name="Bash", input={"command": "echo hello"})
        tr = ToolResult(tool_use_id="tc1", content="hello\n")
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])

        chunks = [user, ai]
        result = analyze_context(chunks)

        assert result[1].total_estimated_tokens >= result[0].total_estimated_tokens

    def test_stats_length_matches_chunks(self):
        chunks = [
            _user_chunk("a"),
            _ai_chunk(),
            _user_chunk("b", chunk_id="u2"),
            _ai_chunk(chunk_id="a2"),
        ]
        result = analyze_context(chunks)
        assert len(result) == len(chunks)


# ---------------------------------------------------------------------------
# Tests: tokens_by_category computation
# ---------------------------------------------------------------------------


class TestTokensByCategory:
    def test_category_keys_present(self):
        user = _user_chunk("hello world")
        tc = ToolCall(id="tc1", name="Bash", input={"command": "ls"})
        tr = ToolResult(tool_use_id="tc1", content="file1\nfile2\n")
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])

        chunks = [user, ai]
        result = analyze_context(chunks)

        cats = result[1].tokens_by_category
        # Should have user-message and tool-output at minimum
        assert "user-message" in cats
        assert "tool-output" in cats

    def test_category_values_positive(self):
        user = _user_chunk("analyze this code please")
        tc = ToolCall(id="tc1", name="Grep", input={"pattern": "import"})
        tr = ToolResult(tool_use_id="tc1", content="import os\nimport sys\n")
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])

        chunks = [user, ai]
        result = analyze_context(chunks)

        for cat, tokens in result[1].tokens_by_category.items():
            assert tokens > 0, f"Category {cat} should have positive tokens"

    def test_category_tokens_sum_to_total(self):
        user = _user_chunk("do something")
        tc = ToolCall(id="tc1", name="Bash", input={"command": "pwd"})
        tr = ToolResult(tool_use_id="tc1", content="/home/user\n")
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])

        chunks = [user, ai]
        result = analyze_context(chunks)

        cat_sum = sum(result[1].tokens_by_category.values())
        assert cat_sum == result[1].total_estimated_tokens

    def test_categories_reset_after_compaction(self):
        user = _user_chunk("phase 1 message")
        ai = _ai_chunk()
        compact = _compact_chunk("summary")
        user2 = _user_chunk("phase 2 message", chunk_id="u2")

        chunks = [user, ai, compact, user2]
        result = analyze_context(chunks)

        # Phase 2 tokens_by_category should only reflect phase 2 content
        phase2_cats = result[3].tokens_by_category
        phase2_total = sum(phase2_cats.values())
        assert phase2_total == result[3].total_estimated_tokens

    def test_empty_chunk_no_categories(self):
        """A system chunk with no relevant content should have empty categories."""
        msg = ParsedMessage(
            uuid="msg-sys",
            parent_uuid=None,
            type=MessageType.SYSTEM,
            timestamp=_TS,
            role="system",
            content="system output",
        )
        chunk = Chunk(
            id="sys1",
            chunk_type=ChunkType.SYSTEM,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg],
        )
        result = analyze_context([chunk])
        assert result[0].tokens_by_category == {}


# ---------------------------------------------------------------------------
# Tests: mixed scenarios
# ---------------------------------------------------------------------------


class TestMixedScenarios:
    def test_full_conversation_flow(self):
        """Test a realistic conversation: user -> AI with tools -> user -> AI."""
        user1 = _user_chunk("Read @config.py and fix the bug")
        tc1 = ToolCall(id="tc1", name="Read", input={"file_path": "/project/config.py"})
        tr1 = ToolResult(tool_use_id="tc1", content="DB_HOST = 'localhost'\n" * 5)
        tc2 = ToolCall(id="tc2", name="Edit", input={"file_path": "/project/config.py", "old_string": "x", "new_string": "y"})
        tr2 = ToolResult(tool_use_id="tc2", content="File edited successfully")
        ai1 = _ai_chunk(tool_calls=[tc1, tc2], tool_results=[tr1, tr2])

        user2 = _user_chunk("Now run the tests", chunk_id="u2")
        tc3 = ToolCall(id="tc3", name="Bash", input={"command": "pytest"})
        tr3 = ToolResult(tool_use_id="tc3", content="3 passed, 0 failed")
        ai2 = _ai_chunk(tool_calls=[tc3], tool_results=[tr3], chunk_id="a2")

        chunks = [user1, ai1, user2, ai2]
        result = analyze_context(chunks)

        assert len(result) == 4
        # All should be phase 1
        assert all(s.phase_number == 1 for s in result)
        # Last chunk should have the most accumulated injections
        assert len(result[3].accumulated_injections) >= len(result[0].accumulated_injections)
        # Total tokens should grow
        assert result[3].total_estimated_tokens > 0

    def test_thinking_plus_tools(self):
        """AI response with both thinking and tool calls."""
        content = [
            {"type": "thinking", "thinking": "I need to read the file first, then analyze."},
            {"type": "text", "text": "Let me look at that file."},
        ]
        tc = ToolCall(id="tc1", name="Read", input={"file_path": "/project/main.py"})
        tr = ToolResult(tool_use_id="tc1", content="def main(): pass")

        msg_assistant = ParsedMessage(
            uuid="msg-a",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            timestamp=_TS,
            role="assistant",
            content=content,
            tool_calls=[tc],
        )
        msg_meta = ParsedMessage(
            uuid="msg-meta",
            parent_uuid=None,
            type=MessageType.USER,
            timestamp=_TS,
            role="user",
            content="",
            is_meta=True,
            tool_results=[tr],
        )
        chunk = Chunk(
            id="a-mixed",
            chunk_type=ChunkType.AI,
            start_time=_TS,
            end_time=_TS,
            metrics=_EMPTY_METRICS,
            messages=[msg_assistant, msg_meta],
        )

        result = analyze_context([chunk])
        categories = {inj.category for inj in result[0].new_injections}
        assert ContextCategory.THINKING_TEXT in categories
        assert ContextCategory.TOOL_OUTPUT in categories

    def test_injection_ids_are_unique(self):
        """All injection IDs should be unique across the entire analysis."""
        user = _user_chunk("check @foo.py")
        tc = ToolCall(id="tc1", name="Bash", input={"command": "ls"})
        tr = ToolResult(tool_use_id="tc1", content="output")
        ai = _ai_chunk(tool_calls=[tc], tool_results=[tr])

        chunks = [user, ai]
        result = analyze_context(chunks)

        all_ids = []
        for stats in result:
            for inj in stats.new_injections:
                all_ids.append(inj.id)
        assert len(all_ids) == len(set(all_ids)), "Injection IDs must be unique"
