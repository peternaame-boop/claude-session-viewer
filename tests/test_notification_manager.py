"""Tests for claude_session_viewer.services.notification_manager."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from claude_session_viewer.services.notification_manager import (
    NotificationManager,
    _DEFAULT_TRIGGERS,
    MAX_HISTORY,
)


def _make_jsonl_line(uuid, role, msg_type, content, is_meta=False, usage=None):
    """Create a single JSONL line."""
    msg = {
        "uuid": uuid,
        "type": msg_type,
        "message": {"role": role, "content": content},
        "timestamp": "2026-02-13T10:00:00.000Z",
        "cwd": "/tmp/test",
        "isMeta": is_meta,
        "isSidechain": False,
        "isCompactSummary": False,
    }
    if usage:
        msg["message"]["usage"] = usage
    return json.dumps(msg)


@pytest.fixture
def notif_manager(qapp, tmp_path, monkeypatch):
    """Create a NotificationManager with isolated settings and history."""
    # Use a temp directory for QSettings
    from PySide6.QtCore import QSettings
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "config"))

    # Redirect history file to tmp
    monkeypatch.setattr(
        "claude_session_viewer.services.notification_manager.DATA_DIR",
        tmp_path / "data",
    )
    monkeypatch.setattr(
        "claude_session_viewer.services.notification_manager.HISTORY_FILE",
        tmp_path / "data" / "notifications.json",
    )

    manager = NotificationManager()
    return manager


# ---------------------------------------------------------------------------
# 1. Default triggers created on first run
# ---------------------------------------------------------------------------

def test_default_triggers(notif_manager):
    """On first run, built-in triggers should be created."""
    triggers = notif_manager.get_triggers()
    assert len(triggers) >= len(_DEFAULT_TRIGGERS)
    names = {t["name"] for t in triggers}
    assert ".env File Access" in names
    assert "Tool Result Error" in names
    assert "High Token Usage (8000)" in names


# ---------------------------------------------------------------------------
# 2. Add trigger
# ---------------------------------------------------------------------------

def test_add_trigger(notif_manager):
    """Adding a trigger increases the count."""
    initial = len(notif_manager.get_triggers())
    notif_manager.add_trigger("Test Pattern", r"TODO", "#ff0000")
    assert len(notif_manager.get_triggers()) == initial + 1


# ---------------------------------------------------------------------------
# 3. Remove trigger
# ---------------------------------------------------------------------------

def test_remove_trigger(notif_manager):
    """Removing a trigger decreases the count."""
    triggers = notif_manager.get_triggers()
    initial = len(triggers)
    notif_manager.remove_trigger(triggers[0]["id"])
    assert len(notif_manager.get_triggers()) == initial - 1


# ---------------------------------------------------------------------------
# 4. Enable/disable trigger
# ---------------------------------------------------------------------------

def test_set_trigger_enabled(notif_manager):
    """Disabling a trigger persists the state."""
    triggers = notif_manager.get_triggers()
    tid = triggers[0]["id"]
    notif_manager.set_trigger_enabled(tid, False)
    updated = notif_manager.get_triggers()
    target = next(t for t in updated if t["id"] == tid)
    assert target["enabled"] is False


# ---------------------------------------------------------------------------
# 5. First check_file sets offset to EOF (no notifications)
# ---------------------------------------------------------------------------

def test_first_check_sets_offset(notif_manager, tmp_path):
    """First check_file call should not fire notifications (starts from EOF)."""
    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "Access the .env file") + "\n"
    )

    fired = []
    notif_manager.notification_fired.connect(lambda e: fired.append(e))
    notif_manager.check_file(str(session))

    assert len(fired) == 0


# ---------------------------------------------------------------------------
# 6. Pattern match fires notification on new content
# ---------------------------------------------------------------------------

def test_pattern_match_fires(notif_manager, tmp_path):
    """New content matching a trigger pattern should fire a notification."""
    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "Hello world") + "\n"
    )

    # First call: sets offset
    notif_manager.check_file(str(session))

    # Append matching content
    with open(session, "a") as f:
        f.write(
            _make_jsonl_line("m2", "user", "user", "Check the .env secrets") + "\n"
        )

    fired = []
    notif_manager.notification_fired.connect(lambda e: fired.append(e))

    with patch.object(notif_manager, "_send_dbus_notification"):
        notif_manager.check_file(str(session))

    assert len(fired) >= 1
    assert ".env" in fired[0]["matched_text"]


# ---------------------------------------------------------------------------
# 7. Disabled trigger does not fire
# ---------------------------------------------------------------------------

def test_disabled_trigger_no_fire(notif_manager, tmp_path):
    """Disabled triggers should not produce notifications."""
    # Disable all triggers
    for t in notif_manager.get_triggers():
        notif_manager.set_trigger_enabled(t["id"], False)

    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "start") + "\n"
    )
    notif_manager.check_file(str(session))

    with open(session, "a") as f:
        f.write(
            _make_jsonl_line("m2", "user", "user", ".env error traceback") + "\n"
        )

    fired = []
    notif_manager.notification_fired.connect(lambda e: fired.append(e))
    notif_manager.check_file(str(session))

    assert len(fired) == 0


# ---------------------------------------------------------------------------
# 8. Token threshold trigger fires
# ---------------------------------------------------------------------------

def test_token_threshold_fires(notif_manager, tmp_path):
    """High token usage trigger fires when output_tokens exceeds threshold."""
    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "start") + "\n"
    )
    notif_manager.check_file(str(session))

    # Append message with high tokens
    usage = {"input_tokens": 100, "output_tokens": 9000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    with open(session, "a") as f:
        f.write(
            _make_jsonl_line("m2", "assistant", "assistant",
                            [{"type": "text", "text": "response"}],
                            usage=usage) + "\n"
        )

    fired = []
    notif_manager.notification_fired.connect(lambda e: fired.append(e))

    with patch.object(notif_manager, "_send_dbus_notification"):
        notif_manager.check_file(str(session))

    # Find the token threshold notification
    token_fires = [f for f in fired if "tokens" in f["matched_text"].lower()]
    assert len(token_fires) >= 1


# ---------------------------------------------------------------------------
# 9. History is recorded
# ---------------------------------------------------------------------------

def test_history_recorded(notif_manager, tmp_path):
    """Fired notifications appear in history."""
    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "start") + "\n"
    )
    notif_manager.check_file(str(session))

    with open(session, "a") as f:
        f.write(
            _make_jsonl_line("m2", "user", "user", "leaked .env data") + "\n"
        )

    with patch.object(notif_manager, "_send_dbus_notification"):
        notif_manager.check_file(str(session))

    history = notif_manager.get_history()
    assert len(history) >= 1
    assert ".env" in history[0]["trigger_name"]


# ---------------------------------------------------------------------------
# 10. Clear history
# ---------------------------------------------------------------------------

def test_clear_history(notif_manager, tmp_path):
    """clear_history empties the history list."""
    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "start") + "\n"
    )
    notif_manager.check_file(str(session))

    with open(session, "a") as f:
        f.write(
            _make_jsonl_line("m2", "user", "user", "check .env") + "\n"
        )

    with patch.object(notif_manager, "_send_dbus_notification"):
        notif_manager.check_file(str(session))

    assert len(notif_manager.get_history()) > 0

    notif_manager.clear_history()
    assert len(notif_manager.get_history()) == 0


# ---------------------------------------------------------------------------
# 11. History max size
# ---------------------------------------------------------------------------

def test_history_max_size(notif_manager):
    """History should not exceed MAX_HISTORY entries."""
    # Directly inject entries
    notif_manager._history = [{"id": str(i)} for i in range(MAX_HISTORY + 50)]
    notif_manager._save_history()

    # Trigger _fire_notification to enforce cap
    with patch.object(notif_manager, "_send_dbus_notification"):
        from claude_session_viewer.types.notifications import NotificationTrigger
        trigger = NotificationTrigger(id="test", name="test", color="#000")
        notif_manager._fire_notification(trigger, "test", "/tmp/test.jsonl")

    assert len(notif_manager._history) <= MAX_HISTORY


# ---------------------------------------------------------------------------
# 12. Nonexistent file does not crash
# ---------------------------------------------------------------------------

def test_nonexistent_file(notif_manager):
    """check_file with a nonexistent path should not raise."""
    notif_manager.check_file("/tmp/does_not_exist_xyz.jsonl")
    # No exception = pass


# ---------------------------------------------------------------------------
# 13. D-Bus notification is called
# ---------------------------------------------------------------------------

def test_dbus_notification_called(notif_manager, tmp_path):
    """_send_dbus_notification is called when a trigger fires."""
    session = tmp_path / "session.jsonl"
    session.write_text(
        _make_jsonl_line("m1", "user", "user", "start") + "\n"
    )
    notif_manager.check_file(str(session))

    with open(session, "a") as f:
        f.write(
            _make_jsonl_line("m2", "user", "user", "found .env leak") + "\n"
        )

    with patch.object(notif_manager, "_send_dbus_notification") as mock_dbus:
        notif_manager.check_file(str(session))
        assert mock_dbus.called


# ---------------------------------------------------------------------------
# 14. triggers_changed signal emitted on add
# ---------------------------------------------------------------------------

def test_triggers_changed_signal(notif_manager):
    """triggers_changed signal is emitted when a trigger is added."""
    signals = []
    notif_manager.triggers_changed.connect(lambda: signals.append(True))
    notif_manager.add_trigger("New", r"pattern", "#000")
    assert len(signals) == 1


# ---------------------------------------------------------------------------
# 15. history_changed signal emitted
# ---------------------------------------------------------------------------

def test_history_changed_signal(notif_manager):
    """history_changed signal is emitted on clear_history."""
    signals = []
    notif_manager.history_changed.connect(lambda: signals.append(True))
    notif_manager.clear_history()
    assert len(signals) == 1
