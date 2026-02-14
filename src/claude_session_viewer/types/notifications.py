"""Notification and search result types."""

from dataclasses import dataclass, field


@dataclass
class NotificationTrigger:
    id: str
    name: str
    enabled: bool = True
    pattern: str = ""           # Regex
    match_fields: list[str] = field(default_factory=list)
    color: str = "#3b82f6"
    token_threshold: int = 0    # 0 = disabled
    match_errors: bool = False
    ignore_patterns: list[str] = field(default_factory=list)
    repo_scope: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    session_id: str
    project_id: str
    session_title: str
    matched_text: str
    context: str
    message_type: str
    timestamp: float
    message_index: int = 0
