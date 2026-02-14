"""Link tool_use calls with their corresponding tool_result responses."""

import logging

from claude_session_viewer.types.messages import ParsedMessage, ToolCall, ToolResult, ToolExecution

logger = logging.getLogger(__name__)


def link_tool_executions(messages: list[ParsedMessage]) -> list[ToolExecution]:
    """Link tool calls to their results across a sequence of messages.

    Scans all messages for tool_use blocks, then finds matching tool_result
    blocks by tool_use_id. Returns a list of ToolExecution pairs.

    Tool calls without results (pending/interrupted) are included with result=None.
    """
    # Collect all tool calls
    call_map: dict[str, tuple[ToolCall, ParsedMessage]] = {}
    for msg in messages:
        for tc in msg.tool_calls:
            call_map[tc.id] = (tc, msg)

    # Match results to calls
    result_map: dict[str, tuple[ToolResult, ParsedMessage]] = {}
    for msg in messages:
        for tr in msg.tool_results:
            result_map[tr.tool_use_id] = (tr, msg)

    # Build execution pairs
    executions: list[ToolExecution] = []
    for tool_id, (call, call_msg) in call_map.items():
        result_info = result_map.get(tool_id)
        result = result_info[0] if result_info else None
        result_msg = result_info[1] if result_info else None

        end_time = result_msg.timestamp if result_msg else None
        duration_ms = 0
        if call_msg.timestamp and end_time:
            delta = (end_time - call_msg.timestamp).total_seconds()
            duration_ms = max(0, int(delta * 1000))

        executions.append(ToolExecution(
            call=call,
            result=result,
            start_time=call_msg.timestamp,
            end_time=end_time,
            duration_ms=duration_ms,
        ))

    # Sort by start time
    executions.sort(key=lambda e: e.start_time or call_msg.timestamp)

    return executions


def find_unmatched_calls(messages: list[ParsedMessage]) -> list[ToolCall]:
    """Find tool calls that have no matching result (pending or lost)."""
    call_ids = set()
    result_ids = set()
    calls: dict[str, ToolCall] = {}

    for msg in messages:
        for tc in msg.tool_calls:
            call_ids.add(tc.id)
            calls[tc.id] = tc
        for tr in msg.tool_results:
            result_ids.add(tr.tool_use_id)

    unmatched_ids = call_ids - result_ids
    return [calls[tid] for tid in unmatched_ids if tid in calls]


def find_orphaned_results(messages: list[ParsedMessage]) -> list[ToolResult]:
    """Find tool results that have no matching call (edge case, shouldn't happen)."""
    call_ids = set()
    orphans = []

    for msg in messages:
        for tc in msg.tool_calls:
            call_ids.add(tc.id)

    for msg in messages:
        for tr in msg.tool_results:
            if tr.tool_use_id not in call_ids:
                orphans.append(tr)

    return orphans


def group_by_tool_name(executions: list[ToolExecution]) -> dict[str, list[ToolExecution]]:
    """Group tool executions by tool name for summary display."""
    groups: dict[str, list[ToolExecution]] = {}
    for ex in executions:
        name = ex.call.name
        if name not in groups:
            groups[name] = []
        groups[name].append(ex)
    return groups
