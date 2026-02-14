"""Tests for live tailing: incremental parsing and chunk updates."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_session_viewer.services.session_manager import SessionManager
from claude_session_viewer.services.jsonl_parser import stream_session_from_offset
from helpers import wait_for_worker


def _make_jsonl_line(uuid, msg_type="user", role="user", content="Hello", parent=None, is_meta=False):
    """Create a single JSONL line for a session file."""
    return json.dumps({
        "uuid": uuid,
        "parentUuid": parent,
        "type": msg_type,
        "message": {"role": role, "content": content},
        "timestamp": "2026-02-13T10:00:00.000Z",
        "cwd": "/home/wiz/test",
        "isMeta": is_meta,
        "isSidechain": False,
        "isCompactSummary": False,
    })


def _write_session(path: Path, lines: list[str]):
    """Write JSONL lines to a file."""
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture
def session_env(tmp_path):
    """Set up a temporary projects dir with one project and session."""
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "-home-wiz-test"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "test-session.jsonl"
    initial_lines = [
        _make_jsonl_line("msg-001", "user", "user", "First question"),
        _make_jsonl_line("msg-002", "assistant", "assistant",
                         [{"type": "text", "text": "First answer"}],
                         parent="msg-001"),
    ]
    _write_session(session_file, initial_lines)

    return {
        "projects_dir": projects_dir,
        "project_dir": project_dir,
        "session_file": session_file,
        "initial_lines": initial_lines,
    }


class TestIncrementalParse:
    def test_stream_from_offset_returns_new_messages(self, session_env):
        """Parsing from an offset only returns messages after that offset."""
        sf = session_env["session_file"]
        initial_size = sf.stat().st_size

        # Append a new line
        with open(sf, "a") as f:
            f.write(_make_jsonl_line("msg-003", "user", "user", "Second question", parent="msg-002") + "\n")

        new_msgs = list(stream_session_from_offset(str(sf), initial_size))
        assert len(new_msgs) == 1
        assert new_msgs[0].uuid == "msg-003"

    def test_no_new_data_returns_empty(self, session_env):
        """Parsing from current EOF returns no messages."""
        sf = session_env["session_file"]
        current_size = sf.stat().st_size

        new_msgs = list(stream_session_from_offset(str(sf), current_size))
        assert len(new_msgs) == 0

    def test_byte_offset_tracked_correctly(self, session_env):
        """File offset updates correctly after incremental reads."""
        sf = session_env["session_file"]
        size_1 = sf.stat().st_size

        # Append two messages
        with open(sf, "a") as f:
            f.write(_make_jsonl_line("msg-003", "user", "user", "Q2") + "\n")
            f.write(_make_jsonl_line("msg-004", "assistant", "assistant",
                                     [{"type": "text", "text": "A2"}]) + "\n")

        size_2 = sf.stat().st_size
        msgs = list(stream_session_from_offset(str(sf), size_1))
        assert len(msgs) == 2

        # Now read from new offset — should be empty
        msgs2 = list(stream_session_from_offset(str(sf), size_2))
        assert len(msgs2) == 0


class TestIncrementalUpdate:
    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_incremental_appends_messages(self, mock_validate, qapp, session_env):
        """_update_conversation appends new messages to cache."""
        m = SessionManager(projects_root=str(session_env["projects_dir"]))
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        sid = m.get_sessions(pid)[0].id
        m.select_session(sid)
        wait_for_worker(m)

        initial_msg_count = len(m._messages[sid])
        initial_chunk_count = len(m.get_chunks(sid))

        # Append a new user + assistant pair
        sf = session_env["session_file"]
        with open(sf, "a") as f:
            f.write(_make_jsonl_line("msg-010", "user", "user", "New question") + "\n")
            f.write(_make_jsonl_line("msg-011", "assistant", "assistant",
                                     [{"type": "text", "text": "New answer"}],
                                     parent="msg-010") + "\n")

        session = m._get_session_map()[sid]
        result = m._update_conversation(session)

        assert result is True
        assert len(m._messages[sid]) == initial_msg_count + 2
        assert len(m.get_chunks(sid)) >= initial_chunk_count
        m.cleanup()

    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_no_new_data_returns_false(self, mock_validate, qapp, session_env):
        """_update_conversation returns False when no new data."""
        m = SessionManager(projects_root=str(session_env["projects_dir"]))
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        sid = m.get_sessions(pid)[0].id
        m.select_session(sid)
        wait_for_worker(m)

        session = m._get_session_map()[sid]
        result = m._update_conversation(session)
        assert result is False
        m.cleanup()

    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_chunk_ids_stable_across_incremental_rebuilds(self, mock_validate, qapp, session_env):
        """Chunk IDs are deterministic — same input produces same IDs."""
        m = SessionManager(projects_root=str(session_env["projects_dir"]))
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        sid = m.get_sessions(pid)[0].id
        m.select_session(sid)
        wait_for_worker(m)

        initial_ids = [c.id for c in m.get_chunks(sid)]

        # Append new messages
        sf = session_env["session_file"]
        with open(sf, "a") as f:
            f.write(_make_jsonl_line("msg-020", "user", "user", "Another Q") + "\n")

        session = m._get_session_map()[sid]
        m._update_conversation(session)
        updated_ids = [c.id for c in m.get_chunks(sid)]

        # Original chunk IDs should still be present as prefix
        assert updated_ids[:len(initial_ids)] == initial_ids
        m.cleanup()

    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_last_ai_chunk_updated_when_response_continues(self, mock_validate, qapp, session_env):
        """When an assistant response is appended, the last AI chunk gets updated."""
        m = SessionManager(projects_root=str(session_env["projects_dir"]))
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        sid = m.get_sessions(pid)[0].id
        m.select_session(sid)
        wait_for_worker(m)

        # Get initial AI chunk message count
        initial_chunks = m.get_chunks(sid)
        ai_chunks = [c for c in initial_chunks if c.chunk_type.value == "ai"]
        assert len(ai_chunks) >= 1
        initial_ai_msg_count = len(ai_chunks[-1].messages)

        # Append another assistant message (continues the response, no new user msg)
        sf = session_env["session_file"]
        with open(sf, "a") as f:
            f.write(_make_jsonl_line("msg-030", "assistant", "assistant",
                                     [{"type": "text", "text": "Continued response"}],
                                     parent="msg-002", is_meta=False) + "\n")

        session = m._get_session_map()[sid]
        m._update_conversation(session)

        updated_chunks = m.get_chunks(sid)
        updated_ai_chunks = [c for c in updated_chunks if c.chunk_type.value == "ai"]
        assert len(updated_ai_chunks[-1].messages) > initial_ai_msg_count
        m.cleanup()

    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_new_user_message_creates_new_chunks(self, mock_validate, qapp, session_env):
        """Appending a new user message creates additional chunks."""
        m = SessionManager(projects_root=str(session_env["projects_dir"]))
        m.scan_projects()
        pid = m.get_projects()[0].id
        m.select_project(pid)
        sid = m.get_sessions(pid)[0].id
        m.select_session(sid)
        wait_for_worker(m)

        initial_chunk_count = len(m.get_chunks(sid))

        # Append user + assistant (creates at least 2 new chunks)
        sf = session_env["session_file"]
        with open(sf, "a") as f:
            f.write(_make_jsonl_line("msg-040", "user", "user", "Brand new question") + "\n")
            f.write(_make_jsonl_line("msg-041", "assistant", "assistant",
                                     [{"type": "text", "text": "Brand new answer"}],
                                     parent="msg-040") + "\n")

        session = m._get_session_map()[sid]
        m._update_conversation(session)

        assert len(m.get_chunks(sid)) > initial_chunk_count
        m.cleanup()
