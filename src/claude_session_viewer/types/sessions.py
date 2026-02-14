"""Session and project metadata types."""

from dataclasses import dataclass


@dataclass
class SessionMetrics:
    duration_ms: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    message_count: int = 0
    tool_call_count: int = 0
    cost_usd: float = 0.0


@dataclass
class Session:
    id: str
    project_id: str
    project_path: str
    file_path: str
    file_size: int
    created_at: float
    modified_at: float
    first_message: str = ""
    message_count: int = 0
    is_ongoing: bool = False
    git_branch: str = ""


@dataclass
class Project:
    id: str          # Encoded directory name
    path: str         # Decoded filesystem path
    name: str         # Last path segment
    session_count: int = 0
