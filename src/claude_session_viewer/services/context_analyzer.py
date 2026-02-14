"""Context analyzer service for token attribution across conversation chunks.

Walks through parsed chunks and computes context token attribution across
six categories: claude-md, mentioned-file, tool-output, thinking-text,
task-coordination, and user-message.
"""

import logging
import re
import uuid as uuid_mod
from copy import deepcopy

from claude_session_viewer.types.chunks import Chunk, ChunkType
from claude_session_viewer.types.context import (
    ContextCategory,
    ContextInjection,
    ContextStats,
)
from claude_session_viewer.types.messages import ParsedMessage, ToolCall, ToolResult
from claude_session_viewer.utils.token_estimator import (
    estimate_tokens,
    estimate_tokens_for_content,
)

logger = logging.getLogger(__name__)

# File patterns that indicate CLAUDE.md / settings config injections
_CLAUDE_MD_PATTERNS = (
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".clauderc",
)

# Tool names that constitute task coordination
_TASK_TOOL_NAMES = frozenset({
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "TaskGet",
    "TaskOutput",
    "Skill",
})

# Regex for @filepath mentions in user text
_FILE_MENTION_RE = re.compile(r"@([\w./\\-]+)")


def analyze_context(chunks: list[Chunk]) -> list[ContextStats]:
    """Analyze context token attribution for each chunk.

    Returns a list of ContextStats with the same length as the input chunks.
    Walks through chunks sequentially, tracking phase boundaries at compaction
    points and accumulating injections within each phase.
    """
    if not chunks:
        return []

    results: list[ContextStats] = []
    phase_number = 1
    accumulated: list[ContextInjection] = []
    tokens_by_cat: dict[str, int] = {}

    for i, chunk in enumerate(chunks):
        stats = ContextStats(phase_number=phase_number)

        if chunk.chunk_type == ChunkType.COMPACT:
            # Compaction boundary: calculate tokens freed, advance phase
            pre_compaction_tokens = sum(inj.estimated_tokens for inj in accumulated)
            summary_tokens = _estimate_compact_summary_tokens(chunk)
            chunk.tokens_freed = max(0, pre_compaction_tokens - summary_tokens)

            stats.total_estimated_tokens = summary_tokens
            stats.accumulated_injections = list(accumulated)
            stats.tokens_by_category = dict(tokens_by_cat)
            results.append(stats)

            # Reset for new phase
            phase_number += 1
            accumulated = []
            tokens_by_cat = {}
            continue

        if chunk.chunk_type == ChunkType.AI:
            new_injections = _analyze_ai_chunk(chunk, chunks, i)
            stats.new_injections = new_injections

            # Add new injections to accumulated
            accumulated.extend(new_injections)

            # Update category totals
            for inj in new_injections:
                cat_key = inj.category.value
                tokens_by_cat[cat_key] = tokens_by_cat.get(cat_key, 0) + inj.estimated_tokens

        elif chunk.chunk_type == ChunkType.USER:
            # User chunks contribute user-message injections
            new_injections = _analyze_user_chunk(chunk, i)
            stats.new_injections = new_injections

            accumulated.extend(new_injections)
            for inj in new_injections:
                cat_key = inj.category.value
                tokens_by_cat[cat_key] = tokens_by_cat.get(cat_key, 0) + inj.estimated_tokens

        stats.accumulated_injections = list(accumulated)
        stats.total_estimated_tokens = sum(inj.estimated_tokens for inj in accumulated)
        stats.tokens_by_category = dict(tokens_by_cat)
        stats.phase_number = phase_number
        results.append(stats)

    return results


def _analyze_ai_chunk(chunk: Chunk, all_chunks: list[Chunk], chunk_index: int) -> list[ContextInjection]:
    """Extract all context injections from an AI chunk."""
    injections: list[ContextInjection] = []

    # Find the preceding user chunk (if any)
    prev_user_chunk = _find_preceding_user_chunk(all_chunks, chunk_index)

    # 1. claude-md: config file reads + system-reminder tags
    injections.extend(_detect_claude_md(chunk, chunk_index))

    # 2. mentioned-file: @filepath patterns in preceding user text
    injections.extend(_detect_mentioned_files(chunk, prev_user_chunk, chunk_index))

    # 3. tool-output: all tool executions
    injections.extend(_detect_tool_output(chunk, chunk_index))

    # 4. thinking-text: thinking content blocks
    injections.extend(_detect_thinking_text(chunk, chunk_index))

    # 5. task-coordination: task/skill tool calls
    injections.extend(_detect_task_coordination(chunk, chunk_index))

    return injections


def _analyze_user_chunk(chunk: Chunk, chunk_index: int) -> list[ContextInjection]:
    """Extract user-message injection from a user chunk."""
    if not chunk.user_text:
        return []

    tokens = estimate_tokens(chunk.user_text)
    if tokens == 0:
        return []

    return [ContextInjection(
        id=_make_id(),
        category=ContextCategory.USER_MESSAGE,
        estimated_tokens=tokens,
        display_name="User message",
        turn_index=chunk_index,
    )]


def _detect_claude_md(chunk: Chunk, turn_index: int) -> list[ContextInjection]:
    """Detect CLAUDE.md and settings file reads, plus system-reminder tags."""
    injections: list[ContextInjection] = []

    for msg in chunk.messages:
        # Check tool calls for Read of config files
        for tc in msg.tool_calls:
            if tc.name == "Read":
                file_path = tc.input.get("file_path", "")
                if _is_claude_md_path(file_path):
                    # Find matching result for token estimation
                    result_tokens = _find_tool_result_tokens(tc.id, chunk)
                    injections.append(ContextInjection(
                        id=_make_id(),
                        category=ContextCategory.CLAUDE_MD,
                        estimated_tokens=result_tokens,
                        path=file_path,
                        display_name=_path_display_name(file_path),
                        turn_index=turn_index,
                    ))

        # Check content blocks for system-reminder tags
        if isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if "<system-reminder>" in text or "system-reminder" in text:
                        tokens = estimate_tokens(text)
                        injections.append(ContextInjection(
                            id=_make_id(),
                            category=ContextCategory.CLAUDE_MD,
                            estimated_tokens=tokens,
                            display_name="System reminder",
                            turn_index=turn_index,
                        ))
        elif isinstance(msg.content, str):
            if "<system-reminder>" in msg.content:
                tokens = estimate_tokens(msg.content)
                injections.append(ContextInjection(
                    id=_make_id(),
                    category=ContextCategory.CLAUDE_MD,
                    estimated_tokens=tokens,
                    display_name="System reminder",
                    turn_index=turn_index,
                ))

    return injections


def _detect_mentioned_files(
    chunk: Chunk,
    prev_user_chunk: Chunk | None,
    turn_index: int,
) -> list[ContextInjection]:
    """Detect @filepath mentions in the preceding user chunk."""
    if prev_user_chunk is None:
        return []

    user_text = prev_user_chunk.user_text
    if not user_text:
        return []

    mentions = _FILE_MENTION_RE.findall(user_text)
    if not mentions:
        return []

    injections: list[ContextInjection] = []
    for filepath in mentions:
        # Try to find a corresponding Read tool call for this file
        result_tokens = _find_read_tokens_for_path(filepath, chunk)
        if result_tokens == 0:
            # Fallback: estimate based on a typical file mention overhead
            result_tokens = estimate_tokens(filepath)

        injections.append(ContextInjection(
            id=_make_id(),
            category=ContextCategory.MENTIONED_FILE,
            estimated_tokens=result_tokens,
            path=filepath,
            display_name=_path_display_name(filepath),
            turn_index=turn_index,
        ))

    return injections


def _detect_tool_output(chunk: Chunk, turn_index: int) -> list[ContextInjection]:
    """Detect tool execution outputs and sum their tokens."""
    injections: list[ContextInjection] = []

    for msg in chunk.messages:
        for tc in msg.tool_calls:
            # Skip task coordination tools (tracked separately)
            if tc.name in _TASK_TOOL_NAMES:
                continue
            # Skip CLAUDE.md reads (tracked separately)
            if tc.name == "Read" and _is_claude_md_path(tc.input.get("file_path", "")):
                continue

            input_tokens = estimate_tokens(str(tc.input))
            result_tokens = _find_tool_result_tokens(tc.id, chunk)
            total = input_tokens + result_tokens

            breakdown = [
                {"label": "input", "tokens": input_tokens},
                {"label": "output", "tokens": result_tokens},
            ]

            injections.append(ContextInjection(
                id=_make_id(),
                category=ContextCategory.TOOL_OUTPUT,
                estimated_tokens=total,
                display_name=tc.name,
                turn_index=turn_index,
                tool_breakdown=breakdown,
            ))

    return injections


def _detect_thinking_text(chunk: Chunk, turn_index: int) -> list[ContextInjection]:
    """Detect thinking content blocks in assistant messages."""
    injections: list[ContextInjection] = []

    for msg in chunk.messages:
        if msg.role != "assistant":
            continue
        if not isinstance(msg.content, list):
            continue

        for block in msg.content:
            if isinstance(block, dict) and block.get("type") == "thinking":
                thinking_text = block.get("thinking", "")
                tokens = estimate_tokens(thinking_text)
                if tokens > 0:
                    injections.append(ContextInjection(
                        id=_make_id(),
                        category=ContextCategory.THINKING_TEXT,
                        estimated_tokens=tokens,
                        display_name="Extended thinking",
                        turn_index=turn_index,
                    ))

    return injections


def _detect_task_coordination(chunk: Chunk, turn_index: int) -> list[ContextInjection]:
    """Detect task coordination tool calls (Task, Skill, etc.)."""
    injections: list[ContextInjection] = []

    for msg in chunk.messages:
        for tc in msg.tool_calls:
            if tc.name not in _TASK_TOOL_NAMES:
                continue

            input_tokens = estimate_tokens(str(tc.input))
            result_tokens = _find_tool_result_tokens(tc.id, chunk)
            total = input_tokens + result_tokens

            injections.append(ContextInjection(
                id=_make_id(),
                category=ContextCategory.TASK_COORDINATION,
                estimated_tokens=total,
                display_name=tc.name,
                turn_index=turn_index,
                tool_breakdown=[
                    {"label": "input", "tokens": input_tokens},
                    {"label": "output", "tokens": result_tokens},
                ],
            ))

    return injections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_preceding_user_chunk(chunks: list[Chunk], current_index: int) -> Chunk | None:
    """Walk backwards from current_index to find the nearest USER chunk."""
    for i in range(current_index - 1, -1, -1):
        if chunks[i].chunk_type == ChunkType.USER:
            return chunks[i]
    return None


def _is_claude_md_path(file_path: str) -> bool:
    """Check if a file path matches known CLAUDE.md / config patterns."""
    if not file_path:
        return False
    for pattern in _CLAUDE_MD_PATTERNS:
        if file_path.endswith(pattern):
            return True
    return False


def _find_tool_result_tokens(tool_use_id: str, chunk: Chunk) -> int:
    """Find the tool result matching a tool_use_id and estimate its tokens."""
    for msg in chunk.messages:
        for tr in msg.tool_results:
            if tr.tool_use_id == tool_use_id:
                return _estimate_tool_result_tokens(tr)
    return 0


def _estimate_tool_result_tokens(tr: ToolResult) -> int:
    """Estimate tokens for a tool result's content."""
    if isinstance(tr.content, str):
        return estimate_tokens(tr.content)
    if isinstance(tr.content, list):
        total = 0
        for item in tr.content:
            if isinstance(item, dict):
                total += estimate_tokens(item.get("text", ""))
            elif isinstance(item, str):
                total += estimate_tokens(item)
        return total
    return 0


def _find_read_tokens_for_path(filepath: str, chunk: Chunk) -> int:
    """Find Read tool call for a filepath and return its result tokens."""
    for msg in chunk.messages:
        for tc in msg.tool_calls:
            if tc.name == "Read":
                call_path = tc.input.get("file_path", "")
                # Match if the call path ends with the mentioned filepath
                if call_path.endswith(filepath) or filepath.endswith(call_path):
                    return _find_tool_result_tokens(tc.id, chunk)
    return 0


def _estimate_compact_summary_tokens(chunk: Chunk) -> int:
    """Estimate tokens in a compact summary chunk's content."""
    total = 0
    for msg in chunk.messages:
        total += estimate_tokens_for_content(msg.content)
    return total


def _path_display_name(path: str) -> str:
    """Extract a short display name from a file path."""
    if not path:
        return ""
    # Return the last component
    parts = path.replace("\\", "/").rstrip("/").split("/")
    return parts[-1] if parts else path


def _make_id() -> str:
    """Generate a unique ID for a context injection."""
    return f"ctx-{uuid_mod.uuid4().hex[:12]}"
