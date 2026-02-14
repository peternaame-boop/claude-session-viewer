"""Chunk types for grouped conversation segments."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_session_viewer.types.messages import ParsedMessage, ToolExecution
    from claude_session_viewer.types.sessions import SessionMetrics
    from claude_session_viewer.types.processes import Process
    from claude_session_viewer.types.context import ContextStats


class ChunkType(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"
    COMPACT = "compact"


class AIGroupStatus(str, Enum):
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    IN_PROGRESS = "in_progress"


@dataclass
class Chunk:
    id: str
    chunk_type: ChunkType
    start_time: datetime
    end_time: datetime
    metrics: "SessionMetrics"
    messages: list["ParsedMessage"]
    # AI-specific
    status: AIGroupStatus = AIGroupStatus.COMPLETE
    tool_executions: list["ToolExecution"] = field(default_factory=list)
    processes: list["Process"] = field(default_factory=list)
    # User-specific
    user_text: str = ""
    commands: list[dict] = field(default_factory=list)
    file_references: list[str] = field(default_factory=list)
    # System-specific
    command_output: str = ""
    # Compact-specific
    tokens_freed: int = 0
    # Context tracking (populated by context_analyzer)
    context_stats: "ContextStats | None" = None
