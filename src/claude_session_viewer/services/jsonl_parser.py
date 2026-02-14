"""Streaming JSONL parser for Claude Code session files."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import orjson

from claude_session_viewer.types.messages import (
    MessageType,
    ParsedMessage,
    TokenUsage,
    ToolCall,
    ToolResult,
)

logger = logging.getLogger(__name__)

# Max size for a single JSONL line (10MB)
MAX_LINE_SIZE = 10 * 1024 * 1024


def parse_session_file(file_path: str | Path) -> list[ParsedMessage]:
    """Parse an entire JSONL session file into a list of ParsedMessage objects."""
    return list(stream_session_file(file_path))


def stream_session_file(file_path: str | Path) -> Iterator[ParsedMessage]:
    """Stream-parse a JSONL session file, yielding ParsedMessage objects.

    Malformed lines are logged and skipped.
    Lines exceeding MAX_LINE_SIZE are skipped with a warning.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning("Session file not found: %s", path)
        return

    line_num = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue

            if len(line) > MAX_LINE_SIZE:
                logger.warning(
                    "Line %d in %s exceeds %dMB, skipping",
                    line_num, path.name, MAX_LINE_SIZE // (1024 * 1024),
                )
                continue

            try:
                raw = orjson.loads(line)
            except orjson.JSONDecodeError as e:
                logger.debug("Malformed JSON at line %d in %s: %s", line_num, path.name, e)
                continue

            if not isinstance(raw, dict):
                continue

            msg = _parse_raw_message(raw)
            if msg is not None:
                yield msg


def stream_session_from_offset(
    file_path: str | Path,
    byte_offset: int,
) -> Iterator[ParsedMessage]:
    """Stream-parse a JSONL file starting from a byte offset.

    Used for incremental parsing when a file is updated.
    Returns an iterator of new messages.
    """
    path = Path(file_path)
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(byte_offset)
        for line in f:
            line = line.strip()
            if not line:
                continue
            if len(line) > MAX_LINE_SIZE:
                continue
            try:
                raw = orjson.loads(line)
            except orjson.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            msg = _parse_raw_message(raw)
            if msg is not None:
                yield msg


def extract_first_user_message(file_path: str | Path, max_lines: int = 100) -> str:
    """Extract the first real user message text from a session file.

    Reads at most max_lines to find it (optimization for metadata scanning).
    """
    path = Path(file_path)
    if not path.exists():
        return ""

    line_count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_count += 1
            if line_count > max_lines:
                break

            line = line.strip()
            if not line:
                continue

            try:
                raw = orjson.loads(line)
            except orjson.JSONDecodeError:
                continue

            if not isinstance(raw, dict):
                continue

            # Real user message: isMeta false, type user
            if raw.get("isMeta", False):
                continue
            if raw.get("type") != "user":
                continue

            message = raw.get("message", {})
            if not isinstance(message, dict):
                continue

            content = message.get("content", "")
            if isinstance(content, str):
                return content[:200].strip()
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            return text[:200]
    return ""


def _parse_raw_message(raw: dict) -> ParsedMessage | None:
    """Parse a raw JSON dict into a ParsedMessage."""
    uuid = raw.get("uuid", "")
    if not uuid:
        return None

    # Parse message type
    type_str = raw.get("type", "")
    try:
        msg_type = MessageType(type_str)
    except ValueError:
        msg_type = MessageType.SYSTEM

    # Parse timestamp
    timestamp = _parse_timestamp(raw.get("timestamp", ""))

    # Parse message body
    message = raw.get("message", {})
    if not isinstance(message, dict):
        message = {}

    role = message.get("role", "")
    content = message.get("content", "")
    model = message.get("model", "")

    # Parse token usage
    usage = None
    raw_usage = message.get("usage")
    if isinstance(raw_usage, dict):
        usage = TokenUsage(
            input_tokens=raw_usage.get("input_tokens", 0),
            output_tokens=raw_usage.get("output_tokens", 0),
            cache_read_input_tokens=raw_usage.get("cache_read_input_tokens", 0),
            cache_creation_input_tokens=raw_usage.get("cache_creation_input_tokens", 0),
        )

    # Extract tool calls and results from content blocks
    tool_calls = []
    tool_results = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tc = ToolCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    input=block.get("input", {}),
                )
                # Check if this is a Task tool call
                if tc.name == "Task":
                    tc.is_task = True
                    tc.task_description = tc.input.get("description", "")
                    tc.task_subagent_type = tc.input.get("subagent_type", "")
                tool_calls.append(tc)
            elif block.get("type") == "tool_result":
                tr = ToolResult(
                    tool_use_id=block.get("tool_use_id", ""),
                    content=block.get("content", ""),
                    is_error=block.get("is_error", False),
                )
                tool_results.append(tr)

    return ParsedMessage(
        uuid=uuid,
        parent_uuid=raw.get("parentUuid"),
        type=msg_type,
        timestamp=timestamp,
        role=role,
        content=content,
        usage=usage,
        model=model,
        cwd=raw.get("cwd", ""),
        git_branch="",  # Resolved later by git_resolver
        agent_id=raw.get("agentId", ""),
        is_sidechain=raw.get("isSidechain", False),
        is_meta=raw.get("isMeta", False),
        is_compact_summary=raw.get("isCompactSummary", False),
        tool_calls=tool_calls,
        tool_results=tool_results,
        source_tool_use_id=raw.get("toolUseResult", {}).get("tool_use_id", "") if isinstance(raw.get("toolUseResult"), dict) else "",
    )


def _parse_timestamp(ts_value) -> datetime:
    """Parse a timestamp from various formats."""
    if isinstance(ts_value, (int, float)):
        return datetime.fromtimestamp(ts_value / 1000 if ts_value > 1e12 else ts_value)
    if isinstance(ts_value, str) and ts_value:
        try:
            # ISO 8601 format: "2026-02-13T12:00:00.000Z"
            return datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
        except ValueError:
            pass
        try:
            return datetime.fromtimestamp(float(ts_value))
        except (ValueError, OSError):
            pass
    return datetime.now()
