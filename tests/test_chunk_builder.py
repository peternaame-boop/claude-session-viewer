"""Tests for claude_session_viewer.services.chunk_builder."""

import pytest

from claude_session_viewer.services.chunk_builder import build_chunks
from claude_session_viewer.services.jsonl_parser import parse_session_file
from claude_session_viewer.types.chunks import ChunkType


# ---------------------------------------------------------------------------
# 1. Simple session chunks
# ---------------------------------------------------------------------------

def test_simple_session_chunks(simple_session_path):
    """Simple session produces User, AI, User, AI, User (5 chunks alternating)."""
    messages = parse_session_file(simple_session_path)
    chunks = build_chunks(messages)

    assert len(chunks) == 5

    expected_types = [
        ChunkType.USER,
        ChunkType.AI,
        ChunkType.USER,
        ChunkType.AI,
        ChunkType.USER,
    ]
    for chunk, ctype in zip(chunks, expected_types):
        assert chunk.chunk_type == ctype


# ---------------------------------------------------------------------------
# 2. Tool session chunks
# ---------------------------------------------------------------------------

def test_tool_session_chunks(tools_session_path):
    """Tool session: User, AI (with tool loop), User, AI. Total 4 chunks.

    msg-t01 -> User chunk
    msg-t02 through msg-t08 -> AI chunk (meta tool results stay in AI buffer)
    msg-t09 -> User chunk
    msg-t10 through msg-t12 -> AI chunk
    """
    messages = parse_session_file(tools_session_path)
    chunks = build_chunks(messages)

    assert len(chunks) == 4

    assert chunks[0].chunk_type == ChunkType.USER
    assert chunks[1].chunk_type == ChunkType.AI
    assert chunks[2].chunk_type == ChunkType.USER
    assert chunks[3].chunk_type == ChunkType.AI

    # First AI chunk should contain msg-t02 through msg-t08 (7 messages)
    assert len(chunks[1].messages) == 7

    # Second AI chunk should contain msg-t10 through msg-t12 (3 messages)
    assert len(chunks[3].messages) == 3


# ---------------------------------------------------------------------------
# 3. Compact creates boundary
# ---------------------------------------------------------------------------

def test_compact_creates_boundary(compaction_session_path):
    """Compact summary creates a CompactChunk between other chunks.

    msg-c01 -> User
    msg-c02 -> AI
    msg-c03 -> User
    msg-c04 -> AI
    msg-c05 -> Compact (isCompactSummary=true, checked before hard noise filter)
    msg-c06 -> User
    msg-c07 -> AI
    """
    messages = parse_session_file(compaction_session_path)
    chunks = build_chunks(messages)

    assert len(chunks) == 7

    chunk_types = [c.chunk_type for c in chunks]
    assert chunk_types == [
        ChunkType.USER, ChunkType.AI,
        ChunkType.USER, ChunkType.AI,
        ChunkType.COMPACT,
        ChunkType.USER, ChunkType.AI,
    ]

    # Verify the compact chunk contains the right message
    compact_chunk = chunks[4]
    assert len(compact_chunk.messages) == 1
    assert compact_chunk.messages[0].uuid == "msg-c05"
    assert compact_chunk.messages[0].is_compact_summary is True


# ---------------------------------------------------------------------------
# 4. Chunk metrics
# ---------------------------------------------------------------------------

def test_chunk_metrics(tools_session_path):
    """AI chunks accumulate token metrics correctly."""
    messages = parse_session_file(tools_session_path)
    chunks = build_chunks(messages)

    # First AI chunk (index 1) covers msg-t02 through msg-t08
    ai_chunk = chunks[1]
    metrics = ai_chunk.metrics

    # message_count should equal number of messages in the chunk
    assert metrics.message_count == len(ai_chunk.messages)

    # Tokens should be positive totals from the assistant messages
    assert metrics.input_tokens > 0
    assert metrics.output_tokens > 0
    assert metrics.total_tokens > 0

    # total_tokens should equal sum of all token fields from usage
    # (input + output + cache_read + cache_creation across all messages)
    expected_total = (
        metrics.input_tokens
        + metrics.output_tokens
        + metrics.cache_read_tokens
        + metrics.cache_creation_tokens
    )
    assert metrics.total_tokens == expected_total


# ---------------------------------------------------------------------------
# 5. Chunk user text
# ---------------------------------------------------------------------------

def test_chunk_user_text(simple_session_path):
    """UserChunks have user_text extracted from the message content."""
    messages = parse_session_file(simple_session_path)
    chunks = build_chunks(messages)

    user_chunks = [c for c in chunks if c.chunk_type == ChunkType.USER]
    assert len(user_chunks) == 3

    assert user_chunks[0].user_text == "Hello, can you help me with a Python script?"
    assert "CSV file" in user_chunks[1].user_text
    assert user_chunks[2].user_text == "Thanks, that looks great!"


# ---------------------------------------------------------------------------
# 6. Empty input
# ---------------------------------------------------------------------------

def test_empty_input():
    """build_chunks with empty list returns empty list."""
    assert build_chunks([]) == []


# ---------------------------------------------------------------------------
# 7. AI chunk tool executions
# ---------------------------------------------------------------------------

def test_ai_chunk_tool_executions(tools_session_path):
    """AI chunks should have tool_executions with matched call/result pairs."""
    messages = parse_session_file(tools_session_path)
    chunks = build_chunks(messages)

    # First AI chunk has Read, Edit, Bash tool calls
    ai_chunk = chunks[1]
    assert len(ai_chunk.tool_executions) > 0

    # Each execution should have both call and result matched
    for tex in ai_chunk.tool_executions:
        assert tex.call is not None
        assert tex.call.name in ("Read", "Edit", "Bash")
        assert tex.result is not None
        assert tex.result.tool_use_id == tex.call.id

    # Second AI chunk has Grep
    ai_chunk2 = chunks[3]
    assert len(ai_chunk2.tool_executions) == 1
    assert ai_chunk2.tool_executions[0].call.name == "Grep"
    assert ai_chunk2.tool_executions[0].result is not None


# ---------------------------------------------------------------------------
# 8. Chunk ordering
# ---------------------------------------------------------------------------

def test_chunk_ordering(tools_session_path):
    """Chunks should be in chronological order."""
    messages = parse_session_file(tools_session_path)
    chunks = build_chunks(messages)

    for i in range(1, len(chunks)):
        assert chunks[i].start_time >= chunks[i - 1].start_time
