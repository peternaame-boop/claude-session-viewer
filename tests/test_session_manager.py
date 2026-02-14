"""Tests for claude_session_viewer.services.session_manager."""

import shutil
from unittest.mock import patch

import pytest

from claude_session_viewer.services.session_manager import SessionManager
from helpers import wait_for_worker


@pytest.fixture
def manager(qapp, tmp_session_dir):
    m = SessionManager(projects_root=str(tmp_session_dir))
    yield m
    m.cleanup()


class TestScanProjects:
    def test_scan_finds_projects(self, manager, tmp_session_dir, simple_session_path):
        # Create a second project dir
        proj2 = tmp_session_dir / "-home-wiz-projects-other"
        proj2.mkdir()
        (proj2 / "some-session.jsonl").write_text(simple_session_path.read_text())

        manager.scan_projects()
        projects = manager.get_projects()
        assert len(projects) >= 1
        names = [p.name for p in projects]
        assert "other" in names

    def test_scan_empty_root(self, qapp, tmp_path):
        empty_root = tmp_path / "empty_projects"
        empty_root.mkdir()
        m = SessionManager(projects_root=str(empty_root))
        m.scan_projects()
        assert len(m.get_projects()) == 0
        m.cleanup()

    def test_scan_nonexistent_root(self, qapp, tmp_path):
        m = SessionManager(projects_root=str(tmp_path / "nonexistent"))
        m.scan_projects()
        assert len(m.get_projects()) == 0
        m.cleanup()


class TestSelectProject:
    def test_select_project_loads_sessions(self, manager, tmp_session_dir, simple_session_path):
        # tmp_session_dir already has one project with test-session.jsonl via the fixture
        project_dir = tmp_session_dir / "-home-wiz-projects-myapp"
        # Ensure a session file exists
        dest = project_dir / "test-session.jsonl"
        if not dest.exists():
            dest.write_text(simple_session_path.read_text())

        manager.scan_projects()
        projects = manager.get_projects()
        assert len(projects) >= 1
        pid = projects[0].id

        manager.select_project(pid)
        sessions = manager.get_sessions(pid)
        assert len(sessions) >= 1
        assert sessions[0].first_message != ""


class TestSelectSession:
    @patch("claude_session_viewer.services.session_manager.validate_session_path", return_value=True)
    def test_select_session_loads_conversation(self, mock_validate, manager, tmp_session_dir, simple_session_path):
        project_dir = tmp_session_dir / "-home-wiz-projects-myapp"
        dest = project_dir / "test-session.jsonl"
        if not dest.exists():
            dest.write_text(simple_session_path.read_text())

        manager.scan_projects()
        pid = manager.get_projects()[0].id
        manager.select_project(pid)
        sessions = manager.get_sessions(pid)
        sid = sessions[0].id

        manager.select_session(sid)
        wait_for_worker(manager)
        chunks = manager.get_chunks(sid)
        assert len(chunks) > 0

    def test_select_same_session_noop(self, manager, tmp_session_dir, simple_session_path):
        project_dir = tmp_session_dir / "-home-wiz-projects-myapp"
        dest = project_dir / "test-session.jsonl"
        if not dest.exists():
            dest.write_text(simple_session_path.read_text())

        manager.scan_projects()
        pid = manager.get_projects()[0].id
        manager.select_project(pid)
        sid = manager.get_sessions(pid)[0].id

        manager.select_session(sid)
        # Second call with same ID should be a noop
        manager.select_session(sid)
        assert manager._current_session_id == sid


class TestCacheUsage:
    def test_cached_sessions_not_reparsed(self, manager, tmp_session_dir, simple_session_path):
        project_dir = tmp_session_dir / "-home-wiz-projects-myapp"
        dest = project_dir / "test-session.jsonl"
        if not dest.exists():
            dest.write_text(simple_session_path.read_text())

        manager.scan_projects()
        pid = manager.get_projects()[0].id

        # First load — parses and caches
        manager._current_project_id = ""  # Reset to allow re-select
        manager.select_project(pid)
        first_sessions = manager.get_sessions(pid)

        # Second load — should use cache (same file size/mtime)
        manager._current_project_id = ""
        manager.select_project(pid)
        second_sessions = manager.get_sessions(pid)

        assert len(first_sessions) == len(second_sessions)
        assert first_sessions[0].first_message == second_sessions[0].first_message
