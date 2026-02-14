"""File system watcher with debounced change signals."""

import logging

from PySide6.QtCore import QObject, Signal, QFileSystemWatcher, QTimer

logger = logging.getLogger(__name__)


class FileWatcher(QObject):
    """Watches Claude project directories for file changes."""

    session_changed = Signal(str)    # file_path
    project_changed = Signal(str)    # directory_path
    projects_root_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._debounce_timers: dict[str, QTimer] = {}
        self._projects_root = ""
        self._watched_sessions: set[str] = set()

        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

    def start(self, projects_root: str):
        """Start watching the projects root directory."""
        self.stop()
        self._projects_root = projects_root
        self._watcher.addPath(projects_root)

    def stop(self):
        """Stop all file watching."""
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        if self._watcher.directories():
            self._watcher.removePaths(self._watcher.directories())
        self._watched_sessions.clear()
        for timer in self._debounce_timers.values():
            timer.stop()
        self._debounce_timers.clear()
        self._projects_root = ""

    def watch_session(self, file_path: str):
        """Add a session file to the watch list."""
        if file_path not in self._watched_sessions:
            self._watcher.addPath(file_path)
            self._watched_sessions.add(file_path)

    def unwatch_session(self, file_path: str):
        """Remove a session file from the watch list."""
        if file_path in self._watched_sessions:
            self._watcher.removePath(file_path)
            self._watched_sessions.discard(file_path)
            # Clean up debounce timer
            if file_path in self._debounce_timers:
                self._debounce_timers[file_path].stop()
                del self._debounce_timers[file_path]

    def watch_all_project_dirs(self, project_dirs: list[str]):
        """Watch all project directories for file changes (active session detection)."""
        # Remove previously watched project dirs (keep root + session files)
        current_dirs = set(self._watcher.directories())
        for d in current_dirs:
            if d != self._projects_root:
                self._watcher.removePath(d)

        # Add all project dirs
        for d in project_dirs:
            if d and d != self._projects_root:
                self._watcher.addPath(d)

    def _on_file_changed(self, path: str):
        """Handle file change with 100ms debounce."""
        # Qt removes the file from the watcher after emitting fileChanged
        # Re-add it after debounce fires
        self._debounce(path, lambda: self._emit_file_changed(path))

    def _on_directory_changed(self, path: str):
        """Handle directory change with 100ms debounce."""
        self._debounce(path, lambda: self._emit_dir_changed(path))

    def _debounce(self, key: str, callback):
        """Debounce a callback by 100ms using the given key."""
        if key in self._debounce_timers:
            self._debounce_timers[key].stop()
        else:
            timer = QTimer(self)
            timer.setSingleShot(True)
            self._debounce_timers[key] = timer

        timer = self._debounce_timers[key]
        try:
            timer.timeout.disconnect()
        except RuntimeError:
            pass
        timer.timeout.connect(callback)
        timer.start(100)

    def _emit_file_changed(self, path: str):
        """Emit the appropriate signal and re-add file to watcher."""
        import os
        if path in self._watched_sessions:
            # Re-add file to watcher (Qt removes it after signal)
            if os.path.exists(path):
                self._watcher.addPath(path)
            self.session_changed.emit(path)

    def _emit_dir_changed(self, path: str):
        """Emit appropriate directory change signal."""
        if path == self._projects_root:
            self.projects_root_changed.emit()
        else:
            self.project_changed.emit(path)
