"""Central session management orchestrator."""

import os
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QThread

from claude_session_viewer.types import Session, Project, Chunk
from claude_session_viewer.services.metadata_cache import MetadataCache
from claude_session_viewer.services.file_watcher import FileWatcher
from claude_session_viewer.services.jsonl_parser import (
    extract_first_user_message,
    stream_session_file,
)
from claude_session_viewer.services.chunk_builder import build_chunks
from claude_session_viewer.services.context_analyzer import analyze_context
from claude_session_viewer.services.subagent_resolver import resolve_subagents
from claude_session_viewer.utils.path_codec import decode_path, extract_project_name
from claude_session_viewer.utils.path_validation import validate_session_path

logger = logging.getLogger(__name__)

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


class SessionManager(QObject):
    """Manages project/session discovery, caching, and loading."""

    projects_loaded = Signal()
    sessions_loaded = Signal(str)  # project_id
    conversation_loaded = Signal(str)  # session_id
    loading_changed = Signal()
    current_project_changed = Signal()
    current_session_changed = Signal()
    session_file_changed = Signal(str)  # file_path

    def __init__(self, parent=None, projects_root: str | None = None):
        super().__init__(parent)
        self._projects_root = Path(projects_root) if projects_root else CLAUDE_PROJECTS_DIR
        self._cache = MetadataCache()
        self._watcher = FileWatcher(self)
        self._loading = False
        self._current_project_id = ""
        self._current_session_id = ""
        self._projects: list[Project] = []
        self._sessions: dict[str, list[Session]] = {}
        self._chunks: dict[str, list[Chunk]] = {}

        # Connect watcher signals
        self._watcher.session_changed.connect(self._on_session_changed)
        self._watcher.project_changed.connect(self._on_project_changed)
        self._watcher.projects_root_changed.connect(self._on_projects_root_changed)

    def _get_loading(self) -> bool:
        return self._loading

    def _set_loading(self, value: bool):
        if self._loading != value:
            self._loading = value
            self.loading_changed.emit()

    loading = Property(bool, _get_loading, notify=loading_changed)

    def _get_current_project_id(self) -> str:
        return self._current_project_id

    currentProjectId = Property(str, _get_current_project_id, notify=current_project_changed)

    def _get_current_session_id(self) -> str:
        return self._current_session_id

    currentSessionId = Property(str, _get_current_session_id, notify=current_session_changed)

    def get_projects(self) -> list[Project]:
        return self._projects

    def get_sessions(self, project_id: str) -> list[Session]:
        return self._sessions.get(project_id, [])

    def get_chunks(self, session_id: str) -> list[Chunk]:
        return self._chunks.get(session_id, [])

    @Slot()
    def scan_projects(self):
        """Scan the projects root directory for Claude projects."""
        self._set_loading(True)
        try:
            projects = []
            if not self._projects_root.exists():
                logger.warning("Projects root does not exist: %s", self._projects_root)
                self._projects = []
                self.projects_loaded.emit()
                return

            for entry in sorted(self._projects_root.iterdir()):
                if not entry.is_dir():
                    continue
                project_id = entry.name
                decoded_path = decode_path(project_id)
                display_name = extract_project_name(project_id)

                # Count .jsonl files directly in this directory (not subdirs)
                session_files = list(entry.glob("*.jsonl"))
                session_count = len(session_files)

                projects.append(Project(
                    id=project_id,
                    path=decoded_path,
                    name=display_name,
                    session_count=session_count,
                ))

            self._projects = projects
            self._watcher.start(str(self._projects_root))
            self.projects_loaded.emit()
        except Exception:
            logger.exception("Failed to scan projects")
        finally:
            self._set_loading(False)

    @Slot(str)
    def select_project(self, project_id: str):
        """Select a project and load its sessions."""
        if self._current_project_id == project_id:
            return
        self._current_project_id = project_id
        self.current_project_changed.emit()
        self._set_loading(True)
        try:
            self._load_sessions(project_id)
            self.sessions_loaded.emit(project_id)
        except Exception:
            logger.exception("Failed to load sessions for %s", project_id)
        finally:
            self._set_loading(False)

    @Slot(str)
    def select_session(self, session_id: str):
        """Select a session and load its conversation."""
        if self._current_session_id == session_id:
            return
        # Unwatch previous session
        if self._current_session_id and self._current_session_id in self._get_session_map():
            old_session = self._get_session_map()[self._current_session_id]
            self._watcher.unwatch_session(old_session.file_path)

        self._current_session_id = session_id
        self.current_session_changed.emit()
        self._set_loading(True)
        try:
            session = self._get_session_map().get(session_id)
            if session:
                self._watcher.watch_session(session.file_path)
                self._load_conversation(session)
                self.conversation_loaded.emit(session_id)
        except Exception:
            logger.exception("Failed to load conversation for %s", session_id)
        finally:
            self._set_loading(False)

    @Slot(str)
    def refresh_session(self, session_id: str):
        """Reload a session's conversation data."""
        session = self._get_session_map().get(session_id)
        if session:
            self._load_conversation(session)
            self.conversation_loaded.emit(session_id)

    def _load_sessions(self, project_id: str):
        """Load all sessions for a project, using cache when possible."""
        project_dir = self._projects_root / project_id
        if not project_dir.exists():
            self._sessions[project_id] = []
            return

        sessions = []
        for jsonl_file in sorted(project_dir.glob("*.jsonl")):
            session_id = jsonl_file.stem
            stat = jsonl_file.stat()

            if not self._cache.is_stale(session_id, stat.st_size, stat.st_mtime):
                cached = self._cache.get(session_id)
                if cached:
                    cached.project_path = decode_path(project_id)
                    sessions.append(cached)
                    continue

            # Parse fresh
            try:
                first_msg = extract_first_user_message(str(jsonl_file))
                # Count messages by streaming (lightweight)
                msg_count = 0
                last_branch = ""
                is_ongoing = False
                for msg in stream_session_file(str(jsonl_file)):
                    msg_count += 1
                    if msg.git_branch:
                        last_branch = msg.git_branch

                session = Session(
                    id=session_id,
                    project_id=project_id,
                    project_path=decode_path(project_id),
                    file_path=str(jsonl_file),
                    file_size=stat.st_size,
                    created_at=stat.st_ctime,
                    modified_at=stat.st_mtime,
                    first_message=first_msg,
                    message_count=msg_count,
                    is_ongoing=is_ongoing,
                    git_branch=last_branch,
                )
                self._cache.put(session)
                sessions.append(session)
            except Exception:
                logger.exception("Failed to parse session %s", jsonl_file)

        # Sort by modified_at descending
        sessions.sort(key=lambda s: s.modified_at, reverse=True)
        self._sessions[project_id] = sessions

    def _load_conversation(self, session: Session):
        """Load full conversation chunks for a session."""
        if not validate_session_path(session.file_path):
            logger.error("Invalid session path: %s", session.file_path)
            return

        messages = list(stream_session_file(session.file_path))
        chunks = build_chunks(messages)

        # Resolve subagents (discover and link agent-*.jsonl files)
        session_dir = str(Path(session.file_path).parent / session.id)
        chunks = resolve_subagents(chunks, session_dir)

        # Compute context stats per chunk
        context_stats_list = analyze_context(chunks)
        for chunk, stats in zip(chunks, context_stats_list):
            chunk.context_stats = stats

        self._chunks[session.id] = chunks

    def _get_session_map(self) -> dict[str, Session]:
        """Get a flat map of all loaded sessions by ID."""
        result = {}
        for sessions in self._sessions.values():
            for s in sessions:
                result[s.id] = s
        return result

    def _on_session_changed(self, file_path: str):
        """Handle file watcher notification for a session file change."""
        self.session_file_changed.emit(file_path)
        if self._current_session_id:
            session = self._get_session_map().get(self._current_session_id)
            if session and session.file_path == file_path:
                self.refresh_session(self._current_session_id)

    def _on_project_changed(self, project_dir: str):
        """Handle file watcher notification for a project directory change."""
        if self._current_project_id:
            project_path = str(self._projects_root / self._current_project_id)
            if project_dir == project_path:
                self.select_project(self._current_project_id)

    def _on_projects_root_changed(self):
        """Handle file watcher notification for the projects root change."""
        self.scan_projects()

    def cleanup(self):
        """Clean up resources."""
        self._watcher.stop()
        self._cache.close()
