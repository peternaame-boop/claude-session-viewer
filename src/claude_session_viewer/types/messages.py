"""Message-level types for parsed JSONL data."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    SUMMARY = "summary"
    FILE_HISTORY = "file-history-snapshot"
    QUEUE_OP = "queue-operation"


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    @property
    def total(self) -> int:
        return (self.input_tokens + self.output_tokens +
                self.cache_read_input_tokens + self.cache_creation_input_tokens)


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict
    is_task: bool = False
    task_description: str = ""
    task_subagent_type: str = ""


@dataclass
class ToolResult:
    tool_use_id: str
    content: Any  # str or list
    is_error: bool = False


@dataclass
class ParsedMessage:
    uuid: str
    parent_uuid: Optional[str]
    type: MessageType
    timestamp: datetime
    role: str = ""
    content: Any = ""
    usage: Optional[TokenUsage] = None
    model: str = ""
    cwd: str = ""
    git_branch: str = ""
    agent_id: str = ""
    is_sidechain: bool = False
    is_meta: bool = False
    is_compact_summary: bool = False
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    source_tool_use_id: str = ""


@dataclass
class ToolExecution:
    """A tool_use paired with its tool_result."""
    call: ToolCall
    result: Optional[ToolResult] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
