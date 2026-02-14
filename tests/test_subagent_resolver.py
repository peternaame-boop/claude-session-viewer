"""Tests for claude_session_viewer.services.subagent_resolver."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_session_viewer.services.subagent_resolver import (
    MEMBER_COLORS,
    _detect_parallel_execution,
    _member_color_map,
    discover_subagents,
    parse_subagent,
    resolve_subagents,
)
from claude_session_viewer.types.chunks import Chunk, ChunkType, AIGroupStatus
from claude_session_viewer.types.messages import (
    MessageType,
    ParsedMessage,
    TokenUsage,
    ToolCall,
    ToolExecution,
    ToolResult,
)
from claude_session_viewer.types.processes import Process
from claude_session_viewer.types.sessions import SessionMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_subagent_jsonl(
    agent_id: str = "abc123",
    session_id: str = "test-session-01",
    messages: list[dict] | None = None,
) -> str:
    """Build JSONL content for a subagent file."""
    if messages is not None:
        return "\n".join(json.dumps(m) for m in messages)

    lines = [
        {
            "parentUuid": None,
            "isSidechain": True,
            "agentId": agent_id,
            "sessionId": session_id,
            "type": "user",
            "message": {
                "role": "user",
                "content": '<teammate-message summary="Search API endpoints" team_name="research" member_name="Explorer">Find all API routes</teammate-message>',
            },
            "uuid": f"sub-{agent_id}-01",
            "timestamp": "2026-01-16T02:07:27.228Z",
            "isMeta": False,
            "isCompactSummary": False,
        },
        {
            "parentUuid": f"sub-{agent_id}-01",
            "isSidechain": True,
            "agentId": agent_id,
            "sessionId": session_id,
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Found 5 API routes in the codebase."},
                ],
                "model": "claude-sonnet-4-5-20250929",
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 50,
                    "cache_read_input_tokens": 100,
                    "cache_creation_input_tokens": 0,
                },
            },
            "uuid": f"sub-{agent_id}-02",
            "timestamp": "2026-01-16T02:07:32.228Z",
            "isMeta": False,
            "isCompactSummary": False,
        },
        {
            "parentUuid": f"sub-{agent_id}-02",
            "isSidechain": True,
            "agentId": agent_id,
            "sessionId": session_id,
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Done scanning."},
                ],
                "model": "claude-sonnet-4-5-20250929",
                "usage": {
                    "input_tokens": 300,
                    "output_tokens": 30,
                    "cache_read_input_tokens": 150,
                    "cache_creation_input_tokens": 0,
                },
            },
            "uuid": f"sub-{agent_id}-03",
            "timestamp": "2026-01-16T02:07:37.228Z",
            "isMeta": False,
            "isCompactSummary": False,
        },
    ]
    return "\n".join(json.dumps(line) for line in lines)


def _write_subagent_file(session_dir: Path, agent_id: str, content: str | None = None) -> Path:
    """Write a subagent JSONL file into session_dir/subagents/."""
    subagents_dir = session_dir / "subagents"
    subagents_dir.mkdir(parents=True, exist_ok=True)
    file_path = subagents_dir / f"agent-{agent_id}.jsonl"
    file_path.write_text(content or _make_subagent_jsonl(agent_id))
    return file_path


def _make_ai_chunk(
    chunk_id: str,
    tool_executions: list[ToolExecution] | None = None,
    messages: list[ParsedMessage] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> Chunk:
    """Create a minimal AI chunk for testing."""
    now = start_time or datetime(2026, 1, 16, 2, 7, 20, tzinfo=timezone.utc)
    end = end_time or datetime(2026, 1, 16, 2, 8, 0, tzinfo=timezone.utc)
    return Chunk(
        id=chunk_id,
        chunk_type=ChunkType.AI,
        start_time=now,
        end_time=end,
        metrics=SessionMetrics(),
        messages=messages or [],
        tool_executions=tool_executions or [],
    )


# ---------------------------------------------------------------------------
# 1. Discover subagents
# ---------------------------------------------------------------------------

def test_discover_subagents(tmp_path):
    """discover_subagents finds agent-*.jsonl files and returns sorted paths."""
    session_dir = tmp_path / "session-01"
    session_dir.mkdir()

    _write_subagent_file(session_dir, "zzz111")
    _write_subagent_file(session_dir, "aaa222")
    _write_subagent_file(session_dir, "mmm333")

    result = discover_subagents(str(session_dir))

    assert len(result) == 3
    # Should be sorted
    filenames = [Path(p).name for p in result]
    assert filenames == ["agent-aaa222.jsonl", "agent-mmm333.jsonl", "agent-zzz111.jsonl"]


# ---------------------------------------------------------------------------
# 2. Discover filters compaction artifacts
# ---------------------------------------------------------------------------

def test_discover_filters_compaction_artifacts(tmp_path):
    """Files starting with 'acompact' are filtered out."""
    session_dir = tmp_path / "session-02"
    subagents_dir = session_dir / "subagents"
    subagents_dir.mkdir(parents=True)

    # Valid subagent file
    (subagents_dir / "agent-abc123.jsonl").write_text("{}")

    # Compaction artifacts that should be filtered
    (subagents_dir / "acompact-001.jsonl").write_text("{}")
    (subagents_dir / "acompact_snapshot.jsonl").write_text("{}")

    # Non-agent files that should be filtered (no agent- prefix)
    (subagents_dir / "other-file.jsonl").write_text("{}")
    (subagents_dir / "readme.txt").write_text("hello")

    result = discover_subagents(str(session_dir))

    assert len(result) == 1
    assert Path(result[0]).name == "agent-abc123.jsonl"


# ---------------------------------------------------------------------------
# 3. Parse subagent
# ---------------------------------------------------------------------------

def test_parse_subagent(tmp_path):
    """parse_subagent extracts Process with correct fields from JSONL."""
    session_dir = tmp_path / "session-03"
    file_path = _write_subagent_file(session_dir, "abc123")

    # Clear color map to avoid cross-test pollution
    _member_color_map.clear()

    process = parse_subagent(str(file_path))

    # ID from filename
    assert process.id == "abc123"
    assert process.file_path == str(file_path)

    # Messages parsed
    assert len(process.messages) == 3

    # Time boundaries
    assert process.start_time == datetime(2026, 1, 16, 2, 7, 27, 228000, tzinfo=timezone.utc)
    assert process.end_time == datetime(2026, 1, 16, 2, 7, 37, 228000, tzinfo=timezone.utc)
    assert process.duration_ms == 10000  # 10 seconds

    # Metrics
    assert process.metrics is not None
    assert process.metrics.message_count == 3
    assert process.metrics.input_tokens == 500  # 200 + 300
    assert process.metrics.output_tokens == 80  # 50 + 30
    assert process.metrics.cache_read_tokens == 250  # 100 + 150
    assert process.metrics.cost_usd > 0

    # Description from teammate-message summary
    assert process.description == "Search API endpoints"

    # Team info
    assert process.team_name == "research"
    assert process.member_name == "Explorer"
    assert process.member_color != ""
    assert process.member_color in MEMBER_COLORS


# ---------------------------------------------------------------------------
# 4. Resolve: result-based linking (Phase 1)
# ---------------------------------------------------------------------------

def test_resolve_result_based_linking(tmp_path):
    """Phase 1: link subagents via agentId in tool result content."""
    session_dir = tmp_path / "session-04"
    _write_subagent_file(session_dir, "abc123")

    # Create a tool result message that references the agent
    tool_result_msg = ParsedMessage(
        uuid="msg-r01",
        parent_uuid="msg-a01",
        type=MessageType.USER,
        timestamp=datetime(2026, 1, 16, 2, 7, 40, tzinfo=timezone.utc),
        role="user",
        content=[{
            "type": "tool_result",
            "tool_use_id": "toolu_task_001",
            "content": "Found 5 routes",
        }],
        is_meta=True,
        tool_results=[
            ToolResult(
                tool_use_id="toolu_task_001",
                content="agentId: agent-abc123 completed successfully",
            ),
        ],
    )

    # Create matching Task tool execution
    task_call = ToolCall(
        id="toolu_task_001",
        name="Task",
        input={"description": "Search API endpoints"},
        is_task=True,
        task_description="Search API endpoints",
    )
    task_exec = ToolExecution(
        call=task_call,
        start_time=datetime(2026, 1, 16, 2, 7, 25, tzinfo=timezone.utc),
    )

    chunk = _make_ai_chunk(
        "chunk-1",
        tool_executions=[task_exec],
        messages=[tool_result_msg],
    )

    result = resolve_subagents([chunk], str(session_dir))

    assert len(result[0].processes) == 1
    linked_proc = result[0].processes[0]
    assert linked_proc.id == "abc123"
    assert linked_proc.parent_task_id == "toolu_task_001"


# ---------------------------------------------------------------------------
# 5. Resolve: description-based linking (Phase 2)
# ---------------------------------------------------------------------------

def test_resolve_description_based_linking(tmp_path):
    """Phase 2: link subagents by matching task description to summary."""
    session_dir = tmp_path / "session-05"
    _write_subagent_file(session_dir, "desc001")

    # Create a Task execution with matching description but no agent ID in results
    task_call = ToolCall(
        id="toolu_task_desc",
        name="Task",
        input={"description": "Search API endpoints"},
        is_task=True,
        task_description="Search API endpoints",
    )
    task_exec = ToolExecution(
        call=task_call,
        start_time=datetime(2026, 1, 16, 2, 7, 25, tzinfo=timezone.utc),
    )

    # No tool results referencing an agent ID
    chunk = _make_ai_chunk("chunk-2", tool_executions=[task_exec], messages=[])

    result = resolve_subagents([chunk], str(session_dir))

    assert len(result[0].processes) == 1
    linked_proc = result[0].processes[0]
    assert linked_proc.id == "desc001"
    assert linked_proc.parent_task_id == "toolu_task_desc"


# ---------------------------------------------------------------------------
# 6. Resolve: positional fallback (Phase 3)
# ---------------------------------------------------------------------------

def test_resolve_positional_fallback(tmp_path):
    """Phase 3: unlinked subagents match to unlinked Tasks by position."""
    session_dir = tmp_path / "session-06"

    # Create subagent with a description that does NOT match any task
    unique_content = _make_subagent_jsonl("pos001", messages=[
        {
            "parentUuid": None,
            "isSidechain": True,
            "agentId": "pos001",
            "sessionId": "s01",
            "type": "user",
            "message": {"role": "user", "content": "Something completely unrelated to any task"},
            "uuid": "sub-pos001-01",
            "timestamp": "2026-01-16T02:07:27.228Z",
            "isMeta": False,
            "isCompactSummary": False,
        },
        {
            "parentUuid": "sub-pos001-01",
            "isSidechain": True,
            "agentId": "pos001",
            "sessionId": "s01",
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "Done.",
                "model": "claude-sonnet-4-5-20250929",
                "usage": {"input_tokens": 10, "output_tokens": 5,
                          "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
            },
            "uuid": "sub-pos001-02",
            "timestamp": "2026-01-16T02:07:30.228Z",
            "isMeta": False,
            "isCompactSummary": False,
        },
    ])
    _write_subagent_file(session_dir, "pos001", unique_content)

    # Task with a totally different description
    task_call = ToolCall(
        id="toolu_task_pos",
        name="Task",
        input={"description": "Completely different task description"},
        is_task=True,
        task_description="Completely different task description",
    )
    task_exec = ToolExecution(
        call=task_call,
        start_time=datetime(2026, 1, 16, 2, 7, 25, tzinfo=timezone.utc),
    )

    chunk = _make_ai_chunk("chunk-3", tool_executions=[task_exec], messages=[])

    result = resolve_subagents([chunk], str(session_dir))

    # Should still link via positional fallback
    assert len(result[0].processes) == 1
    linked_proc = result[0].processes[0]
    assert linked_proc.id == "pos001"
    assert linked_proc.parent_task_id == "toolu_task_pos"


# ---------------------------------------------------------------------------
# 7. Parallel detection
# ---------------------------------------------------------------------------

def test_parallel_detection(tmp_path):
    """Subagents starting within 100ms of each other are marked parallel."""
    session_dir = tmp_path / "session-07"

    # Two subagents starting 50ms apart
    agent_a_content = _make_subagent_jsonl("parA", messages=[
        {
            "parentUuid": None, "isSidechain": True, "agentId": "parA",
            "sessionId": "s01", "type": "user",
            "message": {"role": "user", "content": "Task A"},
            "uuid": "sub-parA-01",
            "timestamp": "2026-01-16T02:07:27.000Z",
            "isMeta": False, "isCompactSummary": False,
        },
        {
            "parentUuid": "sub-parA-01", "isSidechain": True, "agentId": "parA",
            "sessionId": "s01", "type": "assistant",
            "message": {"role": "assistant", "content": "A done.",
                        "model": "claude-sonnet-4-5-20250929",
                        "usage": {"input_tokens": 10, "output_tokens": 5,
                                  "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}},
            "uuid": "sub-parA-02",
            "timestamp": "2026-01-16T02:07:30.000Z",
            "isMeta": False, "isCompactSummary": False,
        },
    ])

    agent_b_content = _make_subagent_jsonl("parB", messages=[
        {
            "parentUuid": None, "isSidechain": True, "agentId": "parB",
            "sessionId": "s01", "type": "user",
            "message": {"role": "user", "content": "Task B"},
            "uuid": "sub-parB-01",
            "timestamp": "2026-01-16T02:07:27.050Z",  # 50ms after agent A
            "isMeta": False, "isCompactSummary": False,
        },
        {
            "parentUuid": "sub-parB-01", "isSidechain": True, "agentId": "parB",
            "sessionId": "s01", "type": "assistant",
            "message": {"role": "assistant", "content": "B done.",
                        "model": "claude-sonnet-4-5-20250929",
                        "usage": {"input_tokens": 10, "output_tokens": 5,
                                  "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}},
            "uuid": "sub-parB-02",
            "timestamp": "2026-01-16T02:07:31.000Z",
            "isMeta": False, "isCompactSummary": False,
        },
    ])

    _write_subagent_file(session_dir, "parA", agent_a_content)
    _write_subagent_file(session_dir, "parB", agent_b_content)

    # Two Task tool executions
    task_a = ToolCall(id="toolu_a", name="Task", input={"description": "Task A"},
                      is_task=True, task_description="Task A")
    task_b = ToolCall(id="toolu_b", name="Task", input={"description": "Task B"},
                      is_task=True, task_description="Task B")
    exec_a = ToolExecution(call=task_a,
                           start_time=datetime(2026, 1, 16, 2, 7, 26, tzinfo=timezone.utc))
    exec_b = ToolExecution(call=task_b,
                           start_time=datetime(2026, 1, 16, 2, 7, 26, 50000, tzinfo=timezone.utc))

    chunk = _make_ai_chunk("chunk-par", tool_executions=[exec_a, exec_b], messages=[])

    result = resolve_subagents([chunk], str(session_dir))

    assert len(result[0].processes) == 2
    for proc in result[0].processes:
        assert proc.is_parallel is True, f"Process {proc.id} should be marked parallel"


# ---------------------------------------------------------------------------
# 8. Empty session (no subagent dir)
# ---------------------------------------------------------------------------

def test_empty_session(tmp_path):
    """When there's no subagents directory, resolve returns chunks unchanged."""
    session_dir = tmp_path / "session-empty"
    session_dir.mkdir()

    chunk = _make_ai_chunk("chunk-empty")
    original_processes = list(chunk.processes)

    result = resolve_subagents([chunk], str(session_dir))

    assert len(result) == 1
    assert result[0].processes == original_processes
    assert result[0].id == "chunk-empty"
