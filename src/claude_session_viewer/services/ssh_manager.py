"""SSH/SFTP manager for remote session access."""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterator

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer

logger = logging.getLogger(__name__)

REMOTE_PROJECTS_PATH = ".claude/projects"
POLL_INTERVAL_MS = 3000


@dataclass
class SshProfile:
    name: str
    host: str
    port: int = 22
    username: str = ""
    key_path: str = ""
    # Derived state (not persisted)
    connected: bool = False


@dataclass
class RemoteFile:
    path: str
    size: int
    mtime: float


class SshManager(QObject):
    """Manages SSH connections and SFTP-based remote session access."""

    connection_changed = Signal()
    remote_projects_loaded = Signal(list)  # list[dict]
    remote_file_changed = Signal(str)  # remote file path
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._connecting = False
        self._active_profile: SshProfile | None = None
        self._conn = None  # asyncssh connection
        self._sftp = None  # asyncssh SFTP client
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._file_sizes: dict[str, int] = {}
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_remote)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def _get_connected(self) -> bool:
        return self._connected

    connected = Property(bool, _get_connected, notify=connection_changed)

    def _get_connecting(self) -> bool:
        return self._connecting

    connecting = Property(bool, _get_connecting, notify=connection_changed)

    def _get_host(self) -> str:
        return self._active_profile.host if self._active_profile else ""

    currentHost = Property(str, _get_host, notify=connection_changed)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @Slot(str, str, int, str, str)
    def connect_ssh(self, name: str, host: str, port: int, username: str, key_path: str):
        """Connect to a remote host via SSH."""
        if self._connected or self._connecting:
            return

        self._active_profile = SshProfile(
            name=name, host=host, port=port,
            username=username, key_path=key_path,
        )
        self._connecting = True
        self.connection_changed.emit()

        # Run asyncssh in a background thread with its own event loop
        self._thread = threading.Thread(target=self._connect_thread, daemon=True)
        self._thread.start()

    def _connect_thread(self):
        """Background thread for SSH connection."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_connect())
        except Exception as e:
            logger.error("SSH connection failed: %s", e)
            self.error_occurred.emit(str(e))
            self._connecting = False
            self.connection_changed.emit()

    async def _async_connect(self):
        """Async SSH connection."""
        import asyncssh

        profile = self._active_profile
        if not profile:
            return

        kwargs = {
            "host": profile.host,
            "port": profile.port,
            "known_hosts": None,  # Accept all for now
        }
        if profile.username:
            kwargs["username"] = profile.username
        if profile.key_path:
            kwargs["client_keys"] = [profile.key_path]

        self._conn = await asyncssh.connect(**kwargs)
        self._sftp = await self._conn.start_sftp_client()

        self._connected = True
        self._connecting = False
        self._active_profile.connected = True
        self.connection_changed.emit()

        # Scan remote projects
        await self._scan_remote_projects()

        # Start polling
        self._poll_timer.start()

    @Slot()
    def disconnect_ssh(self):
        """Disconnect from the remote host."""
        self._poll_timer.stop()
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._sftp = None
        self._connected = False
        self._connecting = False
        self._file_sizes.clear()
        if self._active_profile:
            self._active_profile.connected = False
        self.connection_changed.emit()

    # ------------------------------------------------------------------
    # Remote file operations
    # ------------------------------------------------------------------

    async def _scan_remote_projects(self):
        """Scan remote ~/.claude/projects/ for project directories."""
        if not self._sftp:
            return

        try:
            remote_root = PurePosixPath.home() / REMOTE_PROJECTS_PATH
            # Use ~ expansion
            remote_root_str = f"~/{REMOTE_PROJECTS_PATH}"
            entries = await self._sftp.readdir(remote_root_str)

            projects = []
            for entry in entries:
                if entry.filename.startswith("."):
                    continue
                attrs = entry.attrs
                if attrs.type == 2:  # Directory
                    projects.append({
                        "id": entry.filename,
                        "name": entry.filename.replace("-", "/").lstrip("/").rsplit("/", 1)[-1],
                        "remote": True,
                    })

            self.remote_projects_loaded.emit(projects)

        except Exception as e:
            logger.error("Failed to scan remote projects: %s", e)
            self.error_occurred.emit(f"Remote scan failed: {e}")

    @Slot(str, result=str)
    def read_remote_file(self, remote_path: str) -> str:
        """Read a remote file's contents via SFTP. Blocking."""
        if not self._sftp or not self._loop:
            return ""

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._sftp.open(remote_path, "r"),
                self._loop,
            )
            f = future.result(timeout=10)
            content_future = asyncio.run_coroutine_threadsafe(
                f.read(),
                self._loop,
            )
            content = content_future.result(timeout=30)
            return content
        except Exception as e:
            logger.error("Failed to read remote file %s: %s", remote_path, e)
            return ""

    def _poll_remote(self):
        """Poll remote session files for changes (called by QTimer)."""
        if not self._sftp or not self._loop:
            return

        threading.Thread(target=self._poll_remote_thread, daemon=True).start()

    def _poll_remote_thread(self):
        """Background poll for remote file changes."""
        if not self._sftp or not self._loop:
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._async_poll(),
                self._loop,
            )
            future.result(timeout=10)
        except Exception:
            logger.debug("Remote poll failed", exc_info=True)

    async def _async_poll(self):
        """Check remote files for size changes."""
        if not self._sftp:
            return

        for path, old_size in list(self._file_sizes.items()):
            try:
                attrs = await self._sftp.stat(path)
                if attrs.size != old_size:
                    self._file_sizes[path] = attrs.size
                    self.remote_file_changed.emit(path)
            except Exception:
                pass

    @Slot(str)
    def watch_remote_file(self, remote_path: str):
        """Start watching a remote file for changes."""
        if not self._sftp or not self._loop:
            return
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._sftp.stat(remote_path),
                self._loop,
            )
            attrs = future.result(timeout=5)
            self._file_sizes[remote_path] = attrs.size
        except Exception:
            self._file_sizes[remote_path] = 0

    @Slot(str)
    def unwatch_remote_file(self, remote_path: str):
        """Stop watching a remote file."""
        self._file_sizes.pop(remote_path, None)

    # ------------------------------------------------------------------
    # SSH Config parsing
    # ------------------------------------------------------------------

    @staticmethod
    @Slot(result=list)
    def get_ssh_hosts() -> list[dict]:
        """Parse ~/.ssh/config for host entries."""
        config_path = Path.home() / ".ssh" / "config"
        if not config_path.exists():
            return []

        hosts = []
        current: dict | None = None

        try:
            for line in config_path.read_text().splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                if stripped.lower().startswith("host "):
                    if current:
                        hosts.append(current)
                    hostname = stripped.split(None, 1)[1].strip()
                    if "*" in hostname or "?" in hostname:
                        current = None
                        continue
                    current = {"name": hostname, "host": hostname, "port": 22, "username": "", "keyPath": ""}
                elif current:
                    key, _, value = stripped.partition(" ")
                    key = key.lower().strip()
                    value = value.strip()
                    if key == "hostname":
                        current["host"] = value
                    elif key == "port":
                        current["port"] = int(value)
                    elif key == "user":
                        current["username"] = value
                    elif key == "identityfile":
                        current["keyPath"] = value.replace("~", str(Path.home()))

            if current:
                hosts.append(current)
        except (OSError, ValueError):
            logger.debug("Failed to parse SSH config", exc_info=True)

        return hosts

    def cleanup(self):
        """Clean up SSH resources."""
        self.disconnect_ssh()
