"""Notification trigger system with D-Bus desktop notification dispatch."""

import copy
import json
import logging
import threading
import uuid as uuid_mod
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QSettings

from claude_session_viewer.services.jsonl_parser import stream_session_from_offset
from claude_session_viewer.types.notifications import NotificationTrigger
from claude_session_viewer.utils.regex_validator import validate_regex, safe_match

logger = logging.getLogger(__name__)

MAX_HISTORY = 200
DATA_DIR = Path.home() / ".local" / "share" / "claude-session-viewer"
HISTORY_FILE = DATA_DIR / "notifications.json"

# Built-in trigger definitions
_DEFAULT_TRIGGERS = [
    NotificationTrigger(
        id="builtin-env-access",
        name=".env File Access",
        pattern=r"\.env",
        match_fields=["user", "assistant"],
        color="#ef4444",
    ),
    NotificationTrigger(
        id="builtin-tool-error",
        name="Tool Result Error",
        pattern=r"(?i)error|exception|traceback",
        match_fields=["assistant"],
        color="#f59e0b",
        match_errors=True,
    ),
    NotificationTrigger(
        id="builtin-high-tokens",
        name="High Token Usage (8000)",
        pattern="",
        match_fields=[],
        color="#8b5cf6",
        token_threshold=8000,
    ),
]


class NotificationManager(QObject):
    """Manages notification triggers, matching, and D-Bus dispatch."""

    notification_fired = Signal(dict)
    triggers_changed = Signal()
    history_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._triggers: list[NotificationTrigger] = []
        self._file_offsets: dict[str, int] = {}
        self._history: list[dict] = []
        self._settings = QSettings()

        self._load_triggers()
        self._load_history()

    # ------------------------------------------------------------------
    # Trigger CRUD
    # ------------------------------------------------------------------

    @Slot(result=list)
    def get_triggers(self) -> list[dict]:
        """Return triggers as a list of dicts for QML."""
        return [self._trigger_to_dict(t) for t in self._triggers]

    @Slot(str, str, str)
    def add_trigger(self, name: str, pattern: str, color: str = "#3b82f6"):
        """Add a new user-defined trigger."""
        trigger = NotificationTrigger(
            id=str(uuid_mod.uuid4()),
            name=name,
            pattern=pattern,
            match_fields=["user", "assistant"],
            color=color,
        )
        self._triggers.append(trigger)
        self._save_triggers()
        self.triggers_changed.emit()

    @Slot(str)
    def remove_trigger(self, trigger_id: str):
        """Remove a trigger by ID."""
        self._triggers = [t for t in self._triggers if t.id != trigger_id]
        self._save_triggers()
        self.triggers_changed.emit()

    @Slot(str, bool)
    def set_trigger_enabled(self, trigger_id: str, enabled: bool):
        """Enable or disable a trigger."""
        for t in self._triggers:
            if t.id == trigger_id:
                t.enabled = enabled
                break
        self._save_triggers()
        self.triggers_changed.emit()

    # ------------------------------------------------------------------
    # File checking
    # ------------------------------------------------------------------

    @Slot(str)
    def check_file(self, file_path: str):
        """Check a session file for trigger matches starting from last known offset.

        On first call for a file, starts from end-of-file (don't fire for old content).
        """
        path = Path(file_path)
        if not path.exists():
            return

        file_size = path.stat().st_size

        if file_path not in self._file_offsets:
            # First time seeing this file — start from current end
            self._file_offsets[file_path] = file_size
            return

        offset = self._file_offsets[file_path]
        if offset >= file_size:
            return

        # Parse new messages from offset
        for msg in stream_session_from_offset(file_path, offset):
            self._check_message_triggers(msg, file_path)

        self._file_offsets[file_path] = file_size

    def _check_message_triggers(self, msg, file_path: str):
        """Check a single message against all enabled triggers."""
        for trigger in self._triggers:
            if not trigger.enabled:
                continue

            # Token threshold check
            if trigger.token_threshold > 0 and msg.usage:
                if msg.usage.output_tokens >= trigger.token_threshold:
                    self._fire_notification(
                        trigger,
                        f"Output tokens: {msg.usage.output_tokens}",
                        file_path,
                    )
                    continue

            # Pattern match check
            if not trigger.pattern:
                continue

            text = self._extract_matchable_text(msg, trigger)
            if not text:
                continue

            valid, _ = validate_regex(trigger.pattern)
            if not valid:
                continue

            match = safe_match(trigger.pattern, text)
            if match:
                self._fire_notification(trigger, match.group()[:100], file_path)

    def _extract_matchable_text(self, msg, trigger: NotificationTrigger) -> str:
        """Extract text from a message that should be checked against a trigger."""
        role = msg.role or msg.type.value
        if trigger.match_fields and role not in trigger.match_fields:
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

    def _fire_notification(
        self, trigger: NotificationTrigger, matched_text: str, file_path: str
    ):
        """Record notification and dispatch D-Bus notification."""
        entry = {
            "id": str(uuid_mod.uuid4()),
            "trigger_id": trigger.id,
            "trigger_name": trigger.name,
            "trigger_color": trigger.color,
            "matched_text": matched_text,
            "file_path": file_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._history.append(entry)
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]
        self._save_history()

        self.notification_fired.emit(entry)
        self.history_changed.emit()

        # Send desktop notification in background thread
        self._send_dbus_notification(trigger.name, matched_text)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    @Slot(result=list)
    def get_history(self) -> list[dict]:
        """Return notification history (newest first)."""
        return list(reversed(self._history))

    @Slot()
    def clear_history(self):
        """Clear all notification history."""
        self._history = []
        self._save_history()
        self.history_changed.emit()

    # ------------------------------------------------------------------
    # D-Bus notification
    # ------------------------------------------------------------------

    def _send_dbus_notification(self, summary: str, body: str):
        """Send a desktop notification via D-Bus in a background thread."""

        def _notify():
            try:
                import asyncio
                from dbus_next.aio import MessageBus
                from dbus_next import Variant

                async def _send():
                    bus = await MessageBus().connect()
                    introspection = await bus.introspect(
                        "org.freedesktop.Notifications",
                        "/org/freedesktop/Notifications",
                    )
                    proxy = bus.get_proxy_object(
                        "org.freedesktop.Notifications",
                        "/org/freedesktop/Notifications",
                        introspection,
                    )
                    iface = proxy.get_interface(
                        "org.freedesktop.Notifications"
                    )
                    await iface.call_notify(
                        "Claude Session Viewer",  # app_name
                        0,                        # replaces_id
                        "",                       # app_icon
                        summary,
                        body[:200],
                        [],                       # actions
                        {},                       # hints
                        5000,                     # timeout_ms
                    )
                    bus.disconnect()

                asyncio.run(_send())
            except Exception:
                logger.debug("D-Bus notification failed", exc_info=True)

        thread = threading.Thread(target=_notify, daemon=True)
        thread.start()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_triggers(self):
        """Load triggers from QSettings, creating defaults on first run."""
        self._settings.beginGroup("notifications")
        raw = self._settings.value("triggers", None)
        self._settings.endGroup()

        if raw is not None:
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                self._triggers = [self._dict_to_trigger(d) for d in data]
                return
            except (json.JSONDecodeError, TypeError, KeyError):
                logger.warning("Failed to load triggers from settings, using defaults")

        # First run — create defaults (deep copy to avoid shared mutation)
        self._triggers = copy.deepcopy(_DEFAULT_TRIGGERS)
        self._save_triggers()

    def _save_triggers(self):
        """Persist triggers to QSettings."""
        data = [self._trigger_to_dict(t) for t in self._triggers]
        self._settings.beginGroup("notifications")
        self._settings.setValue("triggers", json.dumps(data))
        self._settings.endGroup()

    def _load_history(self):
        """Load notification history from JSON file."""
        if HISTORY_FILE.exists():
            try:
                self._history = json.loads(HISTORY_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self._history = []
        else:
            self._history = []

    def _save_history(self):
        """Save notification history to JSON file."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            HISTORY_FILE.write_text(json.dumps(self._history))
        except OSError:
            logger.warning("Failed to save notification history", exc_info=True)

    @staticmethod
    def _trigger_to_dict(t: NotificationTrigger) -> dict:
        return {
            "id": t.id,
            "name": t.name,
            "enabled": t.enabled,
            "pattern": t.pattern,
            "matchFields": t.match_fields,
            "color": t.color,
            "tokenThreshold": t.token_threshold,
            "matchErrors": t.match_errors,
        }

    @staticmethod
    def _dict_to_trigger(d: dict) -> NotificationTrigger:
        return NotificationTrigger(
            id=d["id"],
            name=d["name"],
            enabled=d.get("enabled", True),
            pattern=d.get("pattern", ""),
            match_fields=d.get("matchFields", []),
            color=d.get("color", "#3b82f6"),
            token_threshold=d.get("tokenThreshold", 0),
            match_errors=d.get("matchErrors", False),
        )
