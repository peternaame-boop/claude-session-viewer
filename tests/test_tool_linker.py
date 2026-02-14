"""Tests for claude_session_viewer.services.tool_linker."""

from datetime import datetime

import pytest

from claude_session_viewer.services.jsonl_parser import parse_session_file
from claude_session_viewer.services.tool_linker import (
    find_orphaned_results,
    find_unmatched_calls,
    group_by_tool_name,
    link_tool_executions,
)
from claude_session_viewer.types.messages import (
    MessageType,
    ParsedMessage,
    ToolCall,
)


# ---------------------------------------------------------------------------
# 1. Link all tools
# ---------------------------------------------------------------------------

def test_link_all_tools(tools_session_path):
    """Tools session has 4 tool executions (Read, Edit, Bash, Grep), all matched."""
    messages = parse_session_file(tools_session_path)
    executions = link_tool_executions(messages)

    assert len(executions) == 4

    names = {ex.call.name for ex in executions}
    assert names == {"Read", "Edit", "Bash", "Grep"}

    # All should have results matched
    for ex in executions:
        assert ex.result is not None
        assert ex.result.tool_use_id == ex.call.id


# ---------------------------------------------------------------------------
# 2. Link duration calculated
# ---------------------------------------------------------------------------

def test_link_duration_calculated(tools_session_path):
    """duration_ms should be non-negative for matched pairs."""
    messages = parse_session_file(tools_session_path)
    executions = link_tool_executions(messages)

    for ex in executions:
        assert ex.duration_ms >= 0
        assert ex.start_time is not None
        assert ex.end_time is not None


# ---------------------------------------------------------------------------
# 3. Unmatched calls in complete session
# ---------------------------------------------------------------------------

def test_unmatched_calls_in_complete_session(tools_session_path):
    """No unmatched calls in a complete tools session."""
    messages = parse_session_file(tools_session_path)
    unmatched = find_unmatched_calls(messages)
    assert unmatched == []


# ---------------------------------------------------------------------------
# 4. No orphaned results
# ---------------------------------------------------------------------------

def test_no_orphaned_results(tools_session_path):
    """No orphaned results in the tools session."""
    messages = parse_session_file(tools_session_path)
    orphans = find_orphaned_results(messages)
    assert orphans == []


# ---------------------------------------------------------------------------
# 5. Group by tool name
# ---------------------------------------------------------------------------

def test_group_by_tool_name(tools_session_path):
    """group_by_tool_name produces a dict keyed by each tool name."""
    messages = parse_session_file(tools_session_path)
    executions = link_tool_executions(messages)
    groups = group_by_tool_name(executions)

    assert set(groups.keys()) == {"Read", "Edit", "Bash", "Grep"}

    # Each group should have exactly one execution in this fixture
    for name, execs in groups.items():
        assert len(execs) == 1
        assert execs[0].call.name == name


# ---------------------------------------------------------------------------
# 6. Link empty messages
# ---------------------------------------------------------------------------

def test_link_empty_messages():
    """Empty message list returns empty execution list."""
    assert link_tool_executions([]) == []


# ---------------------------------------------------------------------------
# 7. Unmatched call detection
# ---------------------------------------------------------------------------

def test_unmatched_call_detection():
    """A message with a tool call but no result is detected as unmatched."""
    msg = ParsedMessage(
        uuid="test-orphan",
        parent_uuid=None,
        type=MessageType.ASSISTANT,
        timestamp=datetime.now(),
        role="assistant",
        tool_calls=[
            ToolCall(
                id="orphan_001",
                name="Read",
                input={"file_path": "/tmp/x"},
            ),
        ],
    )

    unmatched = find_unmatched_calls([msg])
    assert len(unmatched) == 1
    assert unmatched[0].id == "orphan_001"
    assert unmatched[0].name == "Read"

    # Also verify link_tool_executions includes it with result=None
    executions = link_tool_executions([msg])
    assert len(executions) == 1
    assert executions[0].call.id == "orphan_001"
    assert executions[0].result is None
