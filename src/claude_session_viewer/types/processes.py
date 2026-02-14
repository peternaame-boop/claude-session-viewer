"""Subagent/process types."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_session_viewer.types.messages import ParsedMessage
    from claude_session_viewer.types.sessions import SessionMetrics


@dataclass
class Process:
    """A subagent execution."""
    id: str
    file_path: str
    messages: list["ParsedMessage"] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    metrics: "SessionMetrics | None" = None
    description: str = ""
    subagent_type: str = ""
    is_parallel: bool = False
    parent_task_id: str = ""
    is_ongoing: bool = False
    team_name: str = ""
    member_name: str = ""
    member_color: str = ""
