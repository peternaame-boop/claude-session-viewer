"""Context tracking types for token attribution."""

from dataclasses import dataclass, field
from enum import Enum


class ContextCategory(str, Enum):
    CLAUDE_MD = "claude-md"
    MENTIONED_FILE = "mentioned-file"
    TOOL_OUTPUT = "tool-output"
    THINKING_TEXT = "thinking-text"
    TASK_COORDINATION = "task-coordination"
    USER_MESSAGE = "user-message"


@dataclass
class ContextInjection:
    id: str
    category: ContextCategory
    estimated_tokens: int = 0
    path: str = ""
    display_name: str = ""
    turn_index: int = 0
    tool_breakdown: list[dict] = field(default_factory=list)


@dataclass
class ContextStats:
    new_injections: list[ContextInjection] = field(default_factory=list)
    accumulated_injections: list[ContextInjection] = field(default_factory=list)
    total_estimated_tokens: int = 0
    tokens_by_category: dict[str, int] = field(default_factory=dict)
    phase_number: int = 1
