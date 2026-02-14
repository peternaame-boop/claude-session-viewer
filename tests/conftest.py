"""Shared test fixtures for Claude Session Viewer."""

import os
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def qapp():
    """Create a QGuiApplication for tests that need Qt."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv or ["test"])
    yield app


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def simple_session_path(fixtures_dir) -> Path:
    return fixtures_dir / "simple_session.jsonl"


@pytest.fixture
def tools_session_path(fixtures_dir) -> Path:
    return fixtures_dir / "session_with_tools.jsonl"


@pytest.fixture
def compaction_session_path(fixtures_dir) -> Path:
    return fixtures_dir / "session_with_compaction.jsonl"


@pytest.fixture
def subagents_session_path(fixtures_dir) -> Path:
    return fixtures_dir / "session_with_subagents.jsonl"


@pytest.fixture
def malformed_session_path(fixtures_dir) -> Path:
    return fixtures_dir / "malformed_session.jsonl"


@pytest.fixture
def tmp_session_dir(tmp_path) -> Path:
    """Create a temporary Claude projects directory structure."""
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "-home-wiz-projects-myapp"
    project_dir.mkdir(parents=True)
    return projects_dir


@pytest.fixture
def tmp_session_file(tmp_session_dir, simple_session_path) -> Path:
    """Create a temporary session file in a mock Claude directory."""
    project_dir = tmp_session_dir / "-home-wiz-projects-myapp"
    dest = project_dir / "test-session.jsonl"
    dest.write_text(simple_session_path.read_text())
    return dest
