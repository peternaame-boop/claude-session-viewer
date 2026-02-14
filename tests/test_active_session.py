"""Tests for active session detection and follow-active functionality."""

import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from claude_session_viewer.services.session_manager import SessionManager
from claude_session_viewer.models.session_model import SessionModel
from claude_session_viewer.types import Session
from helpers import wait_for_worker


def _make_jsonl_line(uuid, msg_type="user", role="user", content="Hello", parent=None):
    return json.dumps({
        "uuid": uuid,
        "parentUuid": parent,
        "type": msg_type,
        "message": {"role": role, "content": content},
        "timestamp": "2026-02-13T10:00:00.000Z",
        "cwd": "/home/wiz/test",
        "isMeta": False,
        "isSidechain": False,
        "isCompactSummary": False,
    })


@pytest.fixture
def two_project_env(tmp_path):
    """Set up a temporary projects dir with two projects, each with a session."""
    projects_dir = tmp_path / ".claude" / "projects"

    proj1 = projects_dir / "-home-wiz-proj1"
    proj1.mkdir(parents=True)
    s1 = proj1 / "session-a.jsonl"
    s1.write_text(
        _make_jsonl_line("msg-001", "user", "user", "Project 1 question") + "\n" +
        _make_jsonl_line("msg-002", "assistant", "assistant",
                         [{"type": "text", "text": "Project 1 answer"}],
                         parent="msg-001") + "\n"
    )

    proj2 = projects_dir / "-home-wiz-proj2"
    proj2.mkdir(parents=True)
    s2 = proj2 / "session-b.jsonl"
    s2.write_text(
        _make_jsonl_line("msg-101", "user", "user", "Project 2 question") + "\n" +
        _make_jsonl_line("msg-102", "assistant", "assistant",
                         [{"type": "text", "text": "Project 2 answer"}],
                         parent="msg-101") + "\n"
    )

    return {
        "projects_dir": projects_dir,
        "session_a": s1,
        "session_b": s2,
    }


class TestSessionMarkedActive:
    def test_session_marked_active_on_file_change(self, qapp, two_project_env):
        """Session is_ongoing becomes True when _mark_session_active is called."""
        m = SessionManager(projects_root=str(two_project_env["projects_dir"]))
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        sessions = m.get_sessions(pid)
        session = sessions[0]

        assert session.is_ongoing is False

        m._mark_session_active(session)

        assert session.is_ongoing is True
        assert session.id in m._session_last_write
        m.cleanup()

    def test_session_marked_inactive_after_timeout(self, qapp, two_project_env):
        """Session becomes inactive when last write exceeds timeout."""
        m = SessionManager(projects_root=str(two_project_env["projects_dir"]))
        m._active_timeout_s = 0.1  # 100ms for testing
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        session = m.get_sessions(pid)[0]

        m._mark_session_active(session)
        assert session.is_ongoing is True

        # Simulate time passing
        m._session_last_write[session.id] = time.time() - 1.0

        signals = []
        m.session_activity_changed.connect(lambda sid, active: signals.append((sid, active)))
        m._check_session_activity()

        assert session.is_ongoing is False
        assert len(signals) == 1
        assert signals[0] == (session.id, False)
        m.cleanup()

    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_follow_active_auto_switches_session(self, mock_validate, qapp, two_project_env):
        """With follow_active enabled, _mark_session_active auto-switches to that session."""
        m = SessionManager(projects_root=str(two_project_env["projects_dir"]))
        m._follow_active = True
        m.scan_projects()

        projects = m.get_projects()
        # Select project 1
        m.select_project(projects[0].id)
        sessions_1 = m.get_sessions(projects[0].id)
        m.select_session(sessions_1[0].id)
        wait_for_worker(m)

        current_sid = m._current_session_id

        # Load project 2 sessions into memory
        m._load_sessions(projects[1].id)
        sessions_2 = m.get_sessions(projects[1].id)
        other_session = sessions_2[0]

        # Mark the other project's session as active
        m._mark_session_active(other_session)

        # Should have switched
        assert m._current_session_id == other_session.id
        m.cleanup()

    def test_follow_active_persisted_in_qsettings(self, qapp, two_project_env):
        """followActive setting is persisted via QSettings."""
        m = SessionManager(projects_root=str(two_project_env["projects_dir"]))
        assert m._follow_active is False

        m.set_follow_active(True)
        assert m._follow_active is True

        # Create a new manager — should load the persisted value
        m2 = SessionManager(projects_root=str(two_project_env["projects_dir"]))
        assert m2._follow_active is True

        # Clean up
        m.set_follow_active(False)
        m.cleanup()
        m2.cleanup()


class TestSessionModelTargetedUpdate:
    def test_update_session_emits_targeted_data_changed(self, qapp):
        """update_session emits dataChanged for only the affected row."""
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="Hello", message_count=3, is_ongoing=False),
            Session(id="s2", project_id="p1", project_path="/a", file_path="/a/s2.jsonl",
                    file_size=200, created_at=now, modified_at=now,
                    first_message="World", message_count=5, is_ongoing=False),
        ])

        changed_rows = []
        model.dataChanged.connect(lambda tl, br, roles: changed_rows.append(tl.row()))

        model.update_session("s2", True)

        assert len(changed_rows) == 1
        assert changed_rows[0] == 1  # s2 is at index 1

        # Verify the actual data
        idx = model.index(1, 0)
        assert model.data(idx, SessionModel.IsOngoingRole) is True

    def test_update_session_nonexistent_id_noop(self, qapp):
        """Updating a non-existent session ID does nothing."""
        model = SessionModel()
        now = time.time()
        model.set_sessions([
            Session(id="s1", project_id="p1", project_path="/a", file_path="/a/s1.jsonl",
                    file_size=100, created_at=now, modified_at=now,
                    first_message="Hello", message_count=3, is_ongoing=False),
        ])

        changed_rows = []
        model.dataChanged.connect(lambda tl, br, roles: changed_rows.append(tl.row()))

        model.update_session("nonexistent", True)

        assert len(changed_rows) == 0
