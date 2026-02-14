"""Tests for claude_session_viewer.models (ProjectModel, SessionModel, ConversationModel)."""

import time
from datetime import datetime, timezone

import pytest

from PySide6.QtCore import Qt

from claude_session_viewer.models.project_model import ProjectModel
from claude_session_viewer.models.session_model import SessionModel
from claude_session_viewer.models.conversation_model import ConversationModel, _summarize_input, _summarize_result
from claude_session_viewer.types import (
    Project,
    Session,
    Chunk,
    ChunkType,
    AIGroupStatus,
    SessionMetrics,
    ToolExecution,
    ToolCall,
    ToolResult,
    ParsedMessage,
    MessageType,
)


# ---------------------------------------------------------------------------
# ProjectModel
# ---------------------------------------------------------------------------

class TestProjectModel:
    def test_empty_model(self, qapp):
        model = ProjectModel()
        assert model.rowCount() == 0

    def test_set_projects(self, qapp):
        model = ProjectModel()
        projects = [
            Project(id="p1", path="/home/wiz/a", name="alpha", session_count=3),
            Project(id="p2", path="/home/wiz/b", name="beta", session_count=1),
        ]
        model.set_projects(projects)
        assert model.rowCount() == 2

    def test_data_roles(self, qapp):
        model = ProjectModel()
        model.set_projects([
            Project(id="proj-abc", path="/some/path", name="MyProject", session_count=7),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, ProjectModel.ProjectIdRole) == "proj-abc"
        assert model.data(idx, ProjectModel.ProjectPathRole) == "/some/path"
        assert model.data(idx, ProjectModel.ProjectNameRole) == "MyProject"
        assert model.data(idx, ProjectModel.SessionCountRole) == 7

    def test_get_project_id(self, qapp):
        model = ProjectModel()
        model.set_projects([
            Project(id="p1", path="/a", name="a", session_count=0),
        ])
        assert model.get_project_id(0) == "p1"
        assert model.get_project_id(99) == ""


# ---------------------------------------------------------------------------
# SessionModel
# ---------------------------------------------------------------------------

class TestSessionModel:
    def test_empty_model(self, qapp):
        model = SessionModel()
        assert model.rowCount() == 0

    def test_set_sessions(self, qapp):
        model = SessionModel()
        now = time.time()
        sessions = [
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now, first_message="Hello",
                    message_count=3, is_ongoing=True, git_branch="main"),
        ]
        model.set_sessions(sessions)
        assert model.rowCount() == 1

    def test_data_roles(self, qapp):
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="Fix the bug", message_count=10,
                    is_ongoing=True, git_branch="feature/fix"),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, SessionModel.SessionIdRole) == "s1"
        assert model.data(idx, SessionModel.FirstMessageRole) == "Fix the bug"
        assert model.data(idx, SessionModel.MessageCountRole) == 10
        assert model.data(idx, SessionModel.IsOngoingRole) is True
        assert model.data(idx, SessionModel.GitBranchRole) == "feature/fix"
        assert "ago" in model.data(idx, SessionModel.RelativeTimeRole) or "just now" in model.data(idx, SessionModel.RelativeTimeRole)

    def test_section_role(self, qapp):
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="Recent", message_count=1),
        ])
        idx = model.index(0, 0)
        section = model.data(idx, SessionModel.SectionRole)
        assert section in ("Today", "Yesterday", "This Week", "This Month", "Older")


# ---------------------------------------------------------------------------
# ConversationModel
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_type=ChunkType.USER,
    user_text="Test message",
    tokens_freed=0,
    tool_executions=None,
) -> Chunk:
    now = datetime.now(timezone.utc)
    return Chunk(
        id="chunk-1",
        chunk_type=chunk_type,
        start_time=now,
        end_time=now,
        metrics=SessionMetrics(total_tokens=1000, cost_usd=0.01, duration_ms=5000),
        messages=[],
        user_text=user_text,
        tokens_freed=tokens_freed,
        tool_executions=tool_executions or [],
    )


class TestConversationModel:
    def test_empty_model(self, qapp):
        model = ConversationModel()
        assert model.rowCount() == 0

    def test_set_chunks(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk(), _make_chunk(chunk_type=ChunkType.AI)])
        assert model.rowCount() == 2

    def test_data_chunk_type(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk(chunk_type=ChunkType.USER)])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.ChunkTypeRole) == "user"

    def test_data_user_text(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk(user_text="Hello world")])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.UserTextRole) == "Hello world"

    def test_data_tokens_freed(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk(chunk_type=ChunkType.COMPACT, tokens_freed=50000)])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.TokensFreedRole) == 50000

    def test_data_metrics(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk()])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.TokenCountRole) == 1000
        assert model.data(idx, ConversationModel.DurationRole) == 5000
        assert model.data(idx, ConversationModel.CostRole) == pytest.approx(0.01)

    def test_tool_executions_formatting(self, qapp):
        model = ConversationModel()
        executions = [
            ToolExecution(
                call=ToolCall(id="t1", name="Read", input={"file_path": "/tmp/test.py"}),
                result=ToolResult(tool_use_id="t1", content="file contents here", is_error=False),
                duration_ms=150,
            ),
            ToolExecution(
                call=ToolCall(id="t2", name="Bash", input={"command": "ls -la"}),
                result=ToolResult(tool_use_id="t2", content="error: not found", is_error=True),
                duration_ms=50,
            ),
        ]
        model.set_chunks([_make_chunk(chunk_type=ChunkType.AI, tool_executions=executions)])
        idx = model.index(0, 0)

        assert model.data(idx, ConversationModel.ToolCountRole) == 2

        tool_data = model.data(idx, ConversationModel.ToolExecutionsRole)
        assert isinstance(tool_data, list)
        assert len(tool_data) == 2

        # First tool
        assert tool_data[0]["toolName"] == "Read"
        assert tool_data[0]["isError"] is False
        assert tool_data[0]["durationMs"] == 150
        assert "/tmp/test.py" in tool_data[0]["inputSummary"]

        # Second tool (error)
        assert tool_data[1]["toolName"] == "Bash"
        assert tool_data[1]["isError"] is True

    def test_invalid_index_returns_none(self, qapp):
        model = ConversationModel()
        idx = model.index(99, 0)
        assert model.data(idx, ConversationModel.ChunkTypeRole) is None

    def test_ai_chunk_text_extraction(self, qapp):
        """Test AI text extraction from messages with content blocks."""
        model = ConversationModel()
        now = datetime.now(timezone.utc)
        msg = ParsedMessage(
            uuid="m1", parent_uuid=None, type=MessageType.ASSISTANT,
            timestamp=now, role="assistant",
            content=[{"type": "text", "text": "Here is the answer."}],
            model="claude-sonnet-4-5-20250929",
        )
        chunk = Chunk(
            id="ai-1", chunk_type=ChunkType.AI, start_time=now, end_time=now,
            metrics=SessionMetrics(), messages=[msg],
            status=AIGroupStatus.COMPLETE,
        )
        model.set_chunks([chunk])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.AiTextRole) == "Here is the answer."
        assert model.data(idx, ConversationModel.StatusRole) == "complete"
        assert "sonnet" in model.data(idx, ConversationModel.ModelNameRole)

    def test_system_chunk_text_extraction(self, qapp):
        """Test system text extraction."""
        model = ConversationModel()
        now = datetime.now(timezone.utc)
        msg = ParsedMessage(
            uuid="m1", parent_uuid=None, type=MessageType.SYSTEM,
            timestamp=now, role="system", content="System initialized.",
        )
        chunk = Chunk(
            id="sys-1", chunk_type=ChunkType.SYSTEM, start_time=now, end_time=now,
            metrics=SessionMetrics(), messages=[msg],
        )
        model.set_chunks([chunk])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.SystemTextRole) == "System initialized."

    def test_user_text_fallback_to_message_extraction(self, qapp):
        """Test user text extraction when user_text is empty."""
        model = ConversationModel()
        now = datetime.now(timezone.utc)
        msg = ParsedMessage(
            uuid="m1", parent_uuid=None, type=MessageType.USER,
            timestamp=now, role="human", content="Hello from user",
        )
        chunk = Chunk(
            id="u-1", chunk_type=ChunkType.USER, start_time=now, end_time=now,
            metrics=SessionMetrics(), messages=[msg],
            user_text="",  # Empty, should fallback to extraction
        )
        model.set_chunks([chunk])
        idx = model.index(0, 0)
        result = model.data(idx, ConversationModel.UserTextRole)
        assert "Hello from user" in result

    def test_chunk_id_role(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk()])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.ChunkIdRole) == "chunk-1"

    def test_timestamp_role(self, qapp):
        model = ConversationModel()
        model.set_chunks([_make_chunk()])
        idx = model.index(0, 0)
        ts = model.data(idx, ConversationModel.TimestampRole)
        assert isinstance(ts, str)
        assert len(ts) > 0

    def test_commands_and_filerefs_roles(self, qapp):
        model = ConversationModel()
        now = datetime.now(timezone.utc)
        chunk = Chunk(
            id="u-1", chunk_type=ChunkType.USER, start_time=now, end_time=now,
            metrics=SessionMetrics(), messages=[],
            user_text="test", commands=[{"name": "/help"}],
            file_references=["main.py", "utils.py"],
        )
        model.set_chunks([chunk])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.CommandsRole) == [{"name": "/help"}]
        assert model.data(idx, ConversationModel.FileRefsRole) == ["main.py", "utils.py"]

    def test_ai_text_with_string_content(self, qapp):
        """Test AI text extraction from string content."""
        model = ConversationModel()
        now = datetime.now(timezone.utc)
        msg = ParsedMessage(
            uuid="m1", parent_uuid=None, type=MessageType.ASSISTANT,
            timestamp=now, role="assistant", content="Plain string response.",
        )
        chunk = Chunk(
            id="ai-1", chunk_type=ChunkType.AI, start_time=now, end_time=now,
            metrics=SessionMetrics(), messages=[msg],
        )
        model.set_chunks([chunk])
        idx = model.index(0, 0)
        assert model.data(idx, ConversationModel.AiTextRole) == "Plain string response."

    def test_tool_execution_no_result(self, qapp):
        """Test tool execution formatting when result is None (pending)."""
        model = ConversationModel()
        executions = [
            ToolExecution(
                call=ToolCall(id="t1", name="Read", input={"file_path": "/tmp/test.py"}),
                result=None,
                duration_ms=0,
            ),
        ]
        model.set_chunks([_make_chunk(chunk_type=ChunkType.AI, tool_executions=executions)])
        idx = model.index(0, 0)
        tool_data = model.data(idx, ConversationModel.ToolExecutionsRole)
        assert tool_data[0]["resultSummary"] == ""
        assert tool_data[0]["isError"] is False
        assert tool_data[0]["resultData"] == ""

    def test_tool_execution_rich_fields(self, qapp):
        """Test that enriched tool execution data includes viewer-specific fields."""
        model = ConversationModel()
        executions = [
            ToolExecution(
                call=ToolCall(id="t1", name="Read", input={
                    "file_path": "/home/user/main.py",
                    "offset": 10,
                    "limit": 50,
                }),
                result=ToolResult(tool_use_id="t1", content="file contents", is_error=False),
                duration_ms=100,
            ),
        ]
        model.set_chunks([_make_chunk(chunk_type=ChunkType.AI, tool_executions=executions)])
        idx = model.index(0, 0)
        tool_data = model.data(idx, ConversationModel.ToolExecutionsRole)

        assert tool_data[0]["filePath"] == "/home/user/main.py"
        assert tool_data[0]["fileExtension"] == "py"
        assert tool_data[0]["syntaxDefinition"] == "Python"
        assert tool_data[0]["lineOffset"] == 10
        assert tool_data[0]["lineLimit"] == 50

    def test_tool_execution_edit_diff(self, qapp):
        """Test that Edit tool executions include diff data."""
        model = ConversationModel()
        executions = [
            ToolExecution(
                call=ToolCall(id="t1", name="Edit", input={
                    "file_path": "/tmp/test.py",
                    "old_string": "old code",
                    "new_string": "new code",
                    "replace_all": True,
                }),
                result=ToolResult(tool_use_id="t1", content="File edited", is_error=False),
                duration_ms=50,
            ),
        ]
        model.set_chunks([_make_chunk(chunk_type=ChunkType.AI, tool_executions=executions)])
        idx = model.index(0, 0)
        tool_data = model.data(idx, ConversationModel.ToolExecutionsRole)

        assert tool_data[0]["oldString"] == "old code"
        assert tool_data[0]["newString"] == "new code"
        assert tool_data[0]["replaceAll"] is True
        assert len(tool_data[0]["diffLines"]) > 0
        # Verify diff line structure
        diff_types = {l["type"] for l in tool_data[0]["diffLines"]}
        assert "removed" in diff_types
        assert "added" in diff_types

    def test_tool_execution_bash_fields(self, qapp):
        """Test Bash tool execution has command field."""
        model = ConversationModel()
        executions = [
            ToolExecution(
                call=ToolCall(id="t1", name="Bash", input={
                    "command": "ls -la /tmp",
                    "description": "List temp files",
                }),
                result=ToolResult(tool_use_id="t1", content="total 8\ndrwx 2 user", is_error=False),
                duration_ms=200,
            ),
        ]
        model.set_chunks([_make_chunk(chunk_type=ChunkType.AI, tool_executions=executions)])
        idx = model.index(0, 0)
        tool_data = model.data(idx, ConversationModel.ToolExecutionsRole)

        assert tool_data[0]["command"] == "ls -la /tmp"
        assert tool_data[0]["description"] == "List temp files"

    def test_tool_execution_input_data_is_json(self, qapp):
        """Test inputData is formatted as JSON, not Python repr."""
        model = ConversationModel()
        executions = [
            ToolExecution(
                call=ToolCall(id="t1", name="Read", input={"file_path": "/tmp/test.py"}),
                result=ToolResult(tool_use_id="t1", content="contents", is_error=False),
                duration_ms=10,
            ),
        ]
        model.set_chunks([_make_chunk(chunk_type=ChunkType.AI, tool_executions=executions)])
        idx = model.index(0, 0)
        tool_data = model.data(idx, ConversationModel.ToolExecutionsRole)

        # Should be valid JSON, not Python repr
        import json
        parsed = json.loads(tool_data[0]["inputData"])
        assert parsed["file_path"] == "/tmp/test.py"


# ---------------------------------------------------------------------------
# Summarize helpers
# ---------------------------------------------------------------------------

class TestSummarizeHelpers:
    def test_summarize_input_with_command(self):
        call = ToolCall(id="t1", name="Bash", input={"command": "ls -la"})
        assert _summarize_input(call) == "ls -la"

    def test_summarize_input_with_file_path(self):
        call = ToolCall(id="t1", name="Read", input={"file_path": "/tmp/test.py"})
        assert _summarize_input(call) == "/tmp/test.py"

    def test_summarize_input_with_query(self):
        call = ToolCall(id="t1", name="Search", input={"query": "find something"})
        assert _summarize_input(call) == "find something"

    def test_summarize_input_with_pattern(self):
        call = ToolCall(id="t1", name="Grep", input={"pattern": "def main"})
        assert _summarize_input(call) == "def main"

    def test_summarize_input_empty(self):
        call = ToolCall(id="t1", name="X", input={})
        assert _summarize_input(call) == ""

    def test_summarize_input_fallback(self):
        call = ToolCall(id="t1", name="X", input={"foo": "bar"})
        assert "foo" in _summarize_input(call)

    def test_summarize_result_string(self):
        result = ToolResult(tool_use_id="t1", content="line 1\nline 2")
        assert _summarize_result(result) == "line 1"

    def test_summarize_result_list(self):
        result = ToolResult(tool_use_id="t1", content=[{"type": "text", "text": "output line"}])
        assert _summarize_result(result) == "output line"

    def test_summarize_result_none(self):
        assert _summarize_result(None) == ""

    def test_summarize_result_non_string(self):
        result = ToolResult(tool_use_id="t1", content=12345)
        assert _summarize_result(result) == "12345"


# ---------------------------------------------------------------------------
# SessionModel edge cases
# ---------------------------------------------------------------------------

class TestSessionModelEdgeCases:
    def test_empty_first_message_shows_placeholder(self, qapp):
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="", message_count=0),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, SessionModel.FirstMessageRole) == "(empty session)"

    def test_display_role(self, qapp):
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="Hello", message_count=1),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.DisplayRole) == "Hello"

    def test_invalid_index(self, qapp):
        model = SessionModel()
        idx = model.index(99, 0)
        assert model.data(idx, SessionModel.SessionIdRole) is None

    def test_date_group_role(self, qapp):
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="X", message_count=1),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, SessionModel.DateGroupRole) in ("Today", "Yesterday", "This Week", "This Month", "Older")

    def test_relative_time_minutes(self, qapp):
        model = SessionModel()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=time.time() - 300, modified_at=time.time() - 300,
                    first_message="X", message_count=1),
        ])
        idx = model.index(0, 0)
        rt = model.data(idx, SessionModel.RelativeTimeRole)
        assert "m ago" in rt

    def test_relative_time_hours(self, qapp):
        model = SessionModel()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=time.time() - 7200, modified_at=time.time() - 7200,
                    first_message="X", message_count=1),
        ])
        idx = model.index(0, 0)
        rt = model.data(idx, SessionModel.RelativeTimeRole)
        assert "h ago" in rt

    def test_relative_time_days(self, qapp):
        model = SessionModel()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=time.time() - 172800, modified_at=time.time() - 172800,
                    first_message="X", message_count=1),
        ])
        idx = model.index(0, 0)
        rt = model.data(idx, SessionModel.RelativeTimeRole)
        assert "d ago" in rt

    def test_relative_time_weeks(self, qapp):
        model = SessionModel()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=time.time() - 1209600, modified_at=time.time() - 1209600,
                    first_message="X", message_count=1),
        ])
        idx = model.index(0, 0)
        rt = model.data(idx, SessionModel.RelativeTimeRole)
        assert "w ago" in rt

    def test_relative_time_months(self, qapp):
        model = SessionModel()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=time.time() - 5184000, modified_at=time.time() - 5184000,
                    first_message="X", message_count=1),
        ])
        idx = model.index(0, 0)
        rt = model.data(idx, SessionModel.RelativeTimeRole)
        assert "mo ago" in rt


# ---------------------------------------------------------------------------
# ProjectModel edge cases
# ---------------------------------------------------------------------------

class TestProjectModelEdgeCases:
    def test_display_role(self, qapp):
        model = ProjectModel()
        model.set_projects([
            Project(id="p1", path="/a", name="TestProject", session_count=0),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.DisplayRole) == "TestProject"

    def test_invalid_index(self, qapp):
        model = ProjectModel()
        idx = model.index(99, 0)
        assert model.data(idx, ProjectModel.ProjectIdRole) is None

    def test_unknown_role_returns_none(self, qapp):
        model = ProjectModel()
        model.set_projects([
            Project(id="p1", path="/a", name="X", session_count=0),
        ])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 999) is None
