"""Cross-session full-text search engine."""

import logging
import re
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from claude_session_viewer.services.jsonl_parser import stream_session_file
from claude_session_viewer.types.notifications import SearchResult
from claude_session_viewer.utils.path_codec import decode_path, extract_project_name

logger = logging.getLogger(__name__)

CONTEXT_WINDOW = 50  # chars of context around match


class SearchEngine(QObject):
    """Searches across session files for user and AI text content."""

    results_ready = Signal(list)  # list[SearchResult]

    def __init__(self, parent=None, projects_root: Path | None = None):
        super().__init__(parent)
        self._projects_root: Path | None = projects_root

    def set_projects_root(self, root: Path):
        self._projects_root = root

    @Slot(str, str)
    def search(self, query: str, project_id: str = ""):
        """Search for query text across sessions.

        If project_id is empty, search project names.
        If project_id is set, search session content within that project.
        """
        if not query or not self._projects_root:
            self.results_ready.emit([])
            return

        if not project_id:
            results = self._search_project_names(query)
        else:
            results = self._search_project_sessions(query, project_id)

        self.results_ready.emit(results)

    def _search_project_names(self, query: str) -> list[SearchResult]:
        """Search project display names for the query."""
        results = []
        if not self._projects_root or not self._projects_root.exists():
            return results

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        for entry in sorted(self._projects_root.iterdir()):
            if not entry.is_dir():
                continue
            display_name = extract_project_name(entry.name)
            match = pattern.search(display_name)
            if match:
                start = max(0, match.start() - CONTEXT_WINDOW)
                end = min(len(display_name), match.end() + CONTEXT_WINDOW)
                results.append(SearchResult(
                    session_id="",
                    project_id=entry.name,
                    session_title=display_name,
                    matched_text=match.group(),
                    context=display_name[start:end],
                    message_type="project",
                    timestamp=entry.stat().st_mtime,
                ))
        return results

    def _search_project_sessions(
        self, query: str, project_id: str
    ) -> list[SearchResult]:
        """Search session content within a specific project."""
        results = []
        project_dir = self._projects_root / project_id
        if not project_dir.exists():
            return results

        pattern = re.compile(re.escape(query), re.IGNORECASE)

        # Sort by mtime descending for relevance
        session_files = sorted(
            project_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for jsonl_file in session_files:
            session_id = jsonl_file.stem
            session_title = ""
            msg_index = 0

            for msg in stream_session_file(str(jsonl_file)):
                text = _extract_searchable_text(msg)
                if not text:
                    msg_index += 1
                    continue

                # Capture session title from first real user message
                if not session_title and msg.role == "user" and not msg.is_meta:
                    session_title = text[:100]

                match = pattern.search(text)
                if match:
                    start = max(0, match.start() - CONTEXT_WINDOW)
                    end = min(len(text), match.end() + CONTEXT_WINDOW)
                    results.append(SearchResult(
                        session_id=session_id,
                        project_id=project_id,
                        session_title=session_title or session_id,
                        matched_text=match.group(),
                        context=text[start:end],
                        message_type=msg.role or msg.type.value,
                        timestamp=msg.timestamp.timestamp(),
                        message_index=msg_index,
                    ))
                msg_index += 1

        return results


def _extract_searchable_text(msg) -> str:
    """Extract user and AI text blocks from a message. Skips tool_use, tool_result, thinking."""
    if msg.role not in ("user", "assistant", "human"):
        return ""
    # Skip meta messages (tool results)
    if msg.is_meta:
        return ""

    content = msg.content
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)

    return ""
