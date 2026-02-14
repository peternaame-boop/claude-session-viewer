"""State machine that groups ParsedMessages into display Chunks."""

import logging
import uuid as uuid_mod
from datetime import datetime

from claude_session_viewer.types.messages import ParsedMessage, ToolExecution, MessageType
from claude_session_viewer.types.chunks import Chunk, ChunkType, AIGroupStatus
from claude_session_viewer.types.sessions import SessionMetrics
from claude_session_viewer.utils.message_classifier import (
    classify_message,
    HARD_NOISE_TYPES,
    MessageClassification,
)
from claude_session_viewer.utils.content_sanitizer import (
    extract_user_text,
    extract_slash_commands,
    extract_file_references,
)
from claude_session_viewer.utils.token_estimator import calculate_cost

logger = logging.getLogger(__name__)


def build_chunks(messages: list[ParsedMessage]) -> list[Chunk]:
    """Build display chunks from a list of parsed messages.

    State machine transitions:
    - Real user message (isMeta=False, type=user) -> flush AI buffer, create UserChunk
    - Compact summary -> flush AI buffer, create CompactChunk
    - Assistant message -> add to AI buffer
    - Meta user message (tool results) -> add to AI buffer
    - System message -> create SystemChunk (or add to AI buffer if mid-response)
    - Hard noise (summary, file-history, queue-op) -> skip
    """
    builder = _ChunkBuilder()
    for msg in messages:
        builder.process(msg)
    builder.flush()
    return builder.chunks


class _ChunkBuilder:
    """Internal state machine for chunk building."""

    def __init__(self):
        self.chunks: list[Chunk] = []
        self._ai_buffer: list[ParsedMessage] = []
        self._chunk_counter = 0

    def process(self, msg: ParsedMessage) -> None:
        """Process a single message through the state machine."""
        # Compact summary -> its own chunk (check BEFORE hard noise filter,
        # because compact summaries have type="summary" which is in HARD_NOISE_TYPES)
        if msg.is_compact_summary:
            self._flush_ai_buffer()
            self._create_compact_chunk(msg)
            return

        # Skip hard noise (after compact check, since compact has type="summary")
        if msg.type in HARD_NOISE_TYPES:
            return

        # Real user message: not meta, type user
        if not msg.is_meta and msg.type == MessageType.USER:
            self._flush_ai_buffer()
            self._create_user_chunk(msg)
            return

        # System message (non-meta)
        if not msg.is_meta and msg.type == MessageType.SYSTEM:
            # If we're mid-AI-response, treat as part of it
            if self._ai_buffer:
                self._ai_buffer.append(msg)
            else:
                self._create_system_chunk(msg)
            return

        # Everything else goes into the AI buffer:
        # - Assistant messages (the actual AI responses)
        # - Meta user messages (tool results fed back to AI)
        self._ai_buffer.append(msg)

    def flush(self) -> None:
        """Flush any remaining buffered messages."""
        self._flush_ai_buffer()

    def _next_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk-{self._chunk_counter}"

    def _flush_ai_buffer(self) -> None:
        """Convert buffered AI messages into an AIChunk."""
        if not self._ai_buffer:
            return
        self._create_ai_chunk(self._ai_buffer)
        self._ai_buffer = []

    def _create_user_chunk(self, msg: ParsedMessage) -> None:
        """Create a UserChunk from a real user message."""
        user_text = extract_user_text(msg.content)

        self.chunks.append(Chunk(
            id=self._next_id(),
            chunk_type=ChunkType.USER,
            start_time=msg.timestamp,
            end_time=msg.timestamp,
            metrics=SessionMetrics(message_count=1),
            messages=[msg],
            user_text=user_text,
            commands=extract_slash_commands(user_text),
            file_references=extract_file_references(user_text),
        ))

    def _create_ai_chunk(self, messages: list[ParsedMessage]) -> None:
        """Create an AIChunk from buffered messages."""
        if not messages:
            return

        # Compute metrics across all messages in this chunk
        metrics = SessionMetrics()
        model = ""
        tool_call_map: dict[str, ToolExecution] = {}

        for msg in messages:
            metrics.message_count += 1

            if msg.usage:
                metrics.input_tokens += msg.usage.input_tokens
                metrics.output_tokens += msg.usage.output_tokens
                metrics.cache_read_tokens += msg.usage.cache_read_input_tokens
                metrics.cache_creation_tokens += msg.usage.cache_creation_input_tokens
                metrics.total_tokens += msg.usage.total

            if msg.model and not model:
                model = msg.model

            # Collect tool calls
            for tc in msg.tool_calls:
                metrics.tool_call_count += 1
                tool_call_map[tc.id] = ToolExecution(
                    call=tc,
                    start_time=msg.timestamp,
                )

            # Match tool results to calls
            for tr in msg.tool_results:
                if tr.tool_use_id in tool_call_map:
                    exec_ = tool_call_map[tr.tool_use_id]
                    exec_.result = tr
                    exec_.end_time = msg.timestamp
                    if exec_.start_time and exec_.end_time:
                        delta = (exec_.end_time - exec_.start_time).total_seconds()
                        exec_.duration_ms = int(delta * 1000)

        # Calculate cost
        if model:
            metrics.cost_usd = calculate_cost(
                metrics.input_tokens,
                metrics.output_tokens,
                metrics.cache_read_tokens,
                metrics.cache_creation_tokens,
                model,
            )

        # Duration
        start = messages[0].timestamp
        end = messages[-1].timestamp
        metrics.duration_ms = int((end - start).total_seconds() * 1000)

        # Determine status
        status = self._determine_status(messages)

        self.chunks.append(Chunk(
            id=self._next_id(),
            chunk_type=ChunkType.AI,
            start_time=start,
            end_time=end,
            metrics=metrics,
            messages=messages,
            status=status,
            tool_executions=list(tool_call_map.values()),
        ))

    def _create_system_chunk(self, msg: ParsedMessage) -> None:
        """Create a SystemChunk."""
        command_output = ""
        if isinstance(msg.content, str):
            command_output = msg.content
        elif isinstance(msg.content, list):
            parts = []
            for block in msg.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            command_output = "\n".join(parts)

        self.chunks.append(Chunk(
            id=self._next_id(),
            chunk_type=ChunkType.SYSTEM,
            start_time=msg.timestamp,
            end_time=msg.timestamp,
            metrics=SessionMetrics(message_count=1),
            messages=[msg],
            command_output=command_output,
        ))

    def _create_compact_chunk(self, msg: ParsedMessage) -> None:
        """Create a CompactChunk for context compaction boundaries."""
        self.chunks.append(Chunk(
            id=self._next_id(),
            chunk_type=ChunkType.COMPACT,
            start_time=msg.timestamp,
            end_time=msg.timestamp,
            metrics=SessionMetrics(message_count=1),
            messages=[msg],
        ))

    def _determine_status(self, messages: list[ParsedMessage]) -> AIGroupStatus:
        """Determine the status of an AI chunk based on its messages."""
        if not messages:
            return AIGroupStatus.COMPLETE

        # Check for error indicators
        for msg in messages:
            for tr in msg.tool_results:
                if tr.is_error:
                    return AIGroupStatus.ERROR

        # Check last message for stop reason
        last = messages[-1]
        if isinstance(last.content, list):
            for block in last.content:
                if isinstance(block, dict):
                    stop = block.get("stop_reason", "")
                    if stop == "max_tokens":
                        return AIGroupStatus.INTERRUPTED

        return AIGroupStatus.COMPLETE
