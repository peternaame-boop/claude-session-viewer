"""Central session management orchestrator."""

import os
import time
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer, QSettings, QThread

from claude_session_viewer.types import Session, Project, Chunk
from claude_session_viewer.types.messages import ParsedMessage
from claude_session_viewer.services.metadata_cache import MetadataCache
from claude_session_viewer.services.file_watcher import FileWatcher
from claude_session_viewer.services.jsonl_parser import (
    extract_first_user_message,
    stream_session_file,
    stream_session_from_offset,
)
from claude_session_viewer.services.chunk_builder import build_chunks
from claude_session_viewer.services.context_analyzer import analyze_context
from claude_session_viewer.services.subagent_resolver import resolve_subagents
from claude_session_viewer.utils.path_codec import decode_path, extract_project_name
from claude_session_viewer.utils.path_validation import validate_session_path

logger = logging.getLogger(__name__)

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


class _ConversationWorker(QThread):
    """Background thread for parsing large session files."""

    finished = Signal(str, list, list, int)  # session_id, messages, chunks, file_size

    def __init__(self, session_id: str, file_path: str, parent=None):
        super().__init__(parent)
        self._session_id = session_id
        self._file_path = file_path

    def run(self):
        try:
            messages = list(stream_session_file(self._file_path))
            chunks = build_chunks(messages)

            session_dir = str(Path(self._file_path).parent / self._session_id)
            chunks = resolve_subagents(chunks, session_dir)

            context_stats_list = analyze_context(chunks)
            for chunk, stats in zip(chunks, context_stats_list):
                chunk.context_stats = stats

            file_size = Path(self._file_path).stat().st_size
            self.finished.emit(self._session_id, messages, chunks, file_size)
        except Exception:
            logger.exception("Worker failed to load conversation %s", self._session_id)
            self.finished.emit(self._session_id, [], [], 0)


class SessionManager(QObject):
    """Manages project/session discovery, caching, and loading."""

    projects_loaded = Signal()
    sessions_loaded = Signal(str)  # project_id
    conversation_loaded = Signal(str)  # session_id (full load)
    conversation_updated = Signal(str)  # session_id (incremental update)
    loading_changed = Signal()
    current_project_changed = Signal()
    current_session_changed = Signal()
    session_file_changed = Signal(str)  # file_path
    session_activity_changed = Signal(str, bool)  # session_id, is_ongoing
    follow_active_changed = Signal()

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

        # Live tailing: cached messages + byte offsets per session
        self._messages: dict[str, list[ParsedMessage]] = {}
        self._file_offsets: dict[str, int] = {}

        # Active session tracking
        self._session_last_write: dict[str, float] = {}
        self._active_timeout_s = 30.0
        self._follow_active = False
        self._settings = QSettings()
        self._load_follow_active()

        # Background worker for large session loading
        self._worker: _ConversationWorker | None = None

        # Timer to check for stale active sessions (every 5s)
        self._activity_timer = QTimer(self)
        self._activity_timer.setInterval(5000)
        self._activity_timer.timeout.connect(self._check_session_activity)
        self._activity_timer.start()

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

    def _get_follow_active(self) -> bool:
        return self._follow_active

    followActive = Property(bool, _get_follow_active, notify=follow_active_changed)

    @Slot(bool)
    def set_follow_active(self, value: bool):
        if self._follow_active != value:
            self._follow_active = value
            self._settings.setValue("session/followActive", value)
            self.follow_active_changed.emit()

    def _load_follow_active(self):
        val = self._settings.value("session/followActive", False)
        self._follow_active = val in (True, "true", "True", 1)

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
            # Watch all project dirs for active session detection
            project_dirs = [str(self._projects_root / p.id) for p in projects]
            self._watcher.watch_all_project_dirs(project_dirs)
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
        # Cancel any in-flight worker
        self._cancel_worker()

        # Unwatch previous session
        if self._current_session_id and self._current_session_id in self._get_session_map():
            old_session = self._get_session_map()[self._current_session_id]
            self._watcher.unwatch_session(old_session.file_path)

        self._current_session_id = session_id
        self.current_session_changed.emit()

        session = self._get_session_map().get(session_id)
        if session:
            self._watcher.watch_session(session.file_path)
            self._load_conversation(session)

    @Slot(str)
    def refresh_session(self, session_id: str):
        """Reload a session's conversation data."""
        session = self._get_session_map().get(session_id)
        if session:
            self._load_conversation(session)

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
        """Load conversation chunks for a session in a background thread."""
        if not validate_session_path(session.file_path):
            logger.error("Invalid session path: %s", session.file_path)
            return

        self._set_loading(True)
        self._cancel_worker()

        worker = _ConversationWorker(session.id, session.file_path, self)
        worker.finished.connect(self._on_conversation_loaded)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_conversation_loaded(self, session_id: str, messages: list, chunks: list, file_size: int):
        """Callback when the background worker finishes."""
        self._worker = None

        # Stale result — user switched sessions while loading
        if session_id != self._current_session_id:
            self._set_loading(False)
            return

        self._messages[session_id] = messages
        session = self._get_session_map().get(session_id)
        if session:
            self._file_offsets[session.file_path] = file_size

        self._chunks[session_id] = chunks
        self._set_loading(False)
        self.conversation_loaded.emit(session_id)

    def _cancel_worker(self):
        """Cancel any in-flight conversation loading worker."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.finished.disconnect(self._on_conversation_loaded)
            self._worker.quit()
            self._worker.wait(2000)
            self._worker = None

    def _get_session_map(self) -> dict[str, Session]:
        """Get a flat map of all loaded sessions by ID."""
        result = {}
        for sessions in self._sessions.values():
            for s in sessions:
                result[s.id] = s
        return result

    def _update_conversation(self, session: Session) -> bool:
        """Incrementally update a session's conversation with new messages.

        Returns True if new data was found and chunks were updated.
        """
        path = session.file_path
        try:
            current_size = Path(path).stat().st_size
        except OSError:
            return False

        old_offset = self._file_offsets.get(path, 0)
        if current_size <= old_offset:
            return False

        # Parse only new messages from the byte offset
        new_messages = list(stream_session_from_offset(path, old_offset))
        if not new_messages:
            self._file_offsets[path] = current_size
            return False

        # Append to cached messages
        cached = self._messages.get(session.id, [])
        cached.extend(new_messages)
        self._messages[session.id] = cached
        self._file_offsets[path] = current_size

        # Rebuild all chunks from cached messages (fast, in-memory)
        chunks = build_chunks(cached)

        # Resolve subagents + context analysis
        session_dir = str(Path(path).parent / session.id)
        chunks = resolve_subagents(chunks, session_dir)
        context_stats_list = analyze_context(chunks)
        for chunk, stats in zip(chunks, context_stats_list):
            chunk.context_stats = stats

        self._chunks[session.id] = chunks
        return True

    def _on_session_changed(self, file_path: str):
        """Handle file watcher notification for a session file change."""
        self.session_file_changed.emit(file_path)

        # Mark the session as active
        session = self._find_session_by_path(file_path)
        if session:
            self._mark_session_active(session)

        # Incremental update for the current session
        if self._current_session_id:
            current_session = self._get_session_map().get(self._current_session_id)
            if current_session and current_session.file_path == file_path:
                # Try incremental path if we have cached state
                if current_session.id in self._messages:
                    if self._update_conversation(current_session):
                        self.conversation_updated.emit(self._current_session_id)
                        return
                # Fallback to full reload
                self.refresh_session(self._current_session_id)

    def _on_project_changed(self, project_dir: str):
        """Handle file watcher notification for a project directory change."""
        # Check for recently modified session files in the changed dir
        self._scan_project_dir_for_activity(project_dir)

        if self._current_project_id:
            project_path = str(self._projects_root / self._current_project_id)
            if project_dir == project_path:
                self.select_project(self._current_project_id)

    def _scan_project_dir_for_activity(self, project_dir: str):
        """Scan a project directory for recently modified .jsonl files and mark active."""
        try:
            dir_path = Path(project_dir)
            if not dir_path.is_dir():
                return
            now = time.time()
            for jsonl_file in dir_path.glob("*.jsonl"):
                try:
                    mtime = jsonl_file.stat().st_mtime
                    if now - mtime < 5.0:  # Modified in last 5 seconds
                        session = self._find_session_by_path(str(jsonl_file))
                        if session:
                            self._mark_session_active(session)
                except OSError:
                    continue
        except Exception:
            logger.debug("Error scanning project dir for activity", exc_info=True)

    def _on_projects_root_changed(self):
        """Handle file watcher notification for the projects root change."""
        self.scan_projects()

    # ------------------------------------------------------------------
    # Active session tracking
    # ------------------------------------------------------------------

    def _mark_session_active(self, session: Session):
        """Mark a session as actively being written to."""
        was_active = session.is_ongoing
        session.is_ongoing = True
        self._session_last_write[session.id] = time.time()

        if not was_active:
            self.session_activity_changed.emit(session.id, True)

        # Auto-switch if follow_active is enabled
        if self._follow_active and session.id != self._current_session_id:
            # Switch project if needed
            if session.project_id != self._current_project_id:
                self.select_project(session.project_id)
            self.select_session(session.id)

    def _check_session_activity(self):
        """Timer callback: mark sessions inactive if no writes for _active_timeout_s."""
        now = time.time()
        expired = []
        for session_id, last_write in self._session_last_write.items():
            if now - last_write >= self._active_timeout_s:
                expired.append(session_id)

        for session_id in expired:
            del self._session_last_write[session_id]
            session = self._get_session_map().get(session_id)
            if session and session.is_ongoing:
                session.is_ongoing = False
                self.session_activity_changed.emit(session_id, False)

    def _find_session_by_path(self, file_path: str) -> Session | None:
        """Find a loaded session by its file path."""
        for sessions in self._sessions.values():
            for s in sessions:
                if s.file_path == file_path:
                    return s
        return None

    def cleanup(self):
        """Clean up resources."""
        self._activity_timer.stop()
        self._watcher.stop()
        self._cache.close()
