"""Tests for claude_session_viewer.services.search_engine."""

import json
from pathlib import Path

import pytest

from claude_session_viewer.services.search_engine import SearchEngine


def _make_message(uuid, role, msg_type, content, is_meta=False, timestamp="2026-02-13T10:00:00.000Z"):
    """Helper to create a raw JSONL message dict."""
    msg = {
        "uuid": uuid,
        "type": msg_type,
        "message": {"role": role, "content": content},
        "timestamp": timestamp,
        "cwd": "/tmp/test",
        "isMeta": is_meta,
        "isSidechain": False,
        "isCompactSummary": False,
    }
    return json.dumps(msg)


def _write_session(path: Path, lines: list[str]):
    """Write JSONL lines to a file."""
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture
def search_projects_dir(tmp_path):
    """Create a mock projects directory with two projects and sessions."""
    projects = tmp_path / "projects"
    projects.mkdir()

    # Project 1: myapp
    p1 = projects / "-home-wiz-projects-myapp"
    p1.mkdir()
    _write_session(p1 / "session-001.jsonl", [
        _make_message("m1", "user", "user", "Hello, fix the login bug"),
        _make_message("m2", "assistant", "assistant",
                      [{"type": "text", "text": "I'll fix the authentication error in login.py"}]),
        _make_message("m3", "user", "user", "Thanks, now check the .env file"),
    ])
    _write_session(p1 / "session-002.jsonl", [
        _make_message("m4", "user", "user", "Help me write unit tests"),
        _make_message("m5", "assistant", "assistant",
                      [{"type": "text", "text": "Let me create pytest tests for your module"}]),
    ])

    # Project 2: webapp
    p2 = projects / "-home-wiz-projects-webapp"
    p2.mkdir()
    _write_session(p2 / "session-003.jsonl", [
        _make_message("m6", "user", "user", "Deploy the webapp to production"),
    ])

    return projects


# ---------------------------------------------------------------------------
# 1. Search project names
# ---------------------------------------------------------------------------

def test_search_project_names(search_projects_dir):
    """Searching with no project_id matches project display names."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("myapp", "")

    assert len(results) == 1
    assert results[0].project_id == "-home-wiz-projects-myapp"
    assert results[0].message_type == "project"


# ---------------------------------------------------------------------------
# 2. Search project names - no match
# ---------------------------------------------------------------------------

def test_search_project_names_no_match(search_projects_dir):
    """No projects match a nonexistent query."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("nonexistent", "")

    assert len(results) == 0


# ---------------------------------------------------------------------------
# 3. Search session content - user text
# ---------------------------------------------------------------------------

def test_search_session_user_text(search_projects_dir):
    """Search finds matches in user messages."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("login bug", "-home-wiz-projects-myapp")

    assert len(results) == 1
    assert results[0].session_id == "session-001"
    assert "login bug" in results[0].matched_text.lower()


# ---------------------------------------------------------------------------
# 4. Search session content - AI text
# ---------------------------------------------------------------------------

def test_search_session_ai_text(search_projects_dir):
    """Search finds matches in assistant text blocks."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("authentication error", "-home-wiz-projects-myapp")

    assert len(results) == 1
    assert results[0].message_type == "assistant"


# ---------------------------------------------------------------------------
# 5. Search is case-insensitive
# ---------------------------------------------------------------------------

def test_search_case_insensitive(search_projects_dir):
    """Search is case-insensitive."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("PYTEST", "-home-wiz-projects-myapp")

    assert len(results) == 1
    assert "pytest" in results[0].context.lower()


# ---------------------------------------------------------------------------
# 6. Search across multiple sessions
# ---------------------------------------------------------------------------

def test_search_multiple_sessions(search_projects_dir):
    """Search returns results from multiple sessions in the same project."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    # "the" appears in both sessions
    engine.search(".env", "-home-wiz-projects-myapp")

    assert len(results) == 1
    assert results[0].session_id == "session-001"


# ---------------------------------------------------------------------------
# 7. Empty query returns no results
# ---------------------------------------------------------------------------

def test_empty_query(search_projects_dir):
    """An empty query returns no results."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("", "-home-wiz-projects-myapp")

    assert len(results) == 0


# ---------------------------------------------------------------------------
# 8. Nonexistent project returns empty
# ---------------------------------------------------------------------------

def test_nonexistent_project(search_projects_dir):
    """Searching a nonexistent project returns empty results."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("hello", "-home-wiz-fake-project")

    assert len(results) == 0


# ---------------------------------------------------------------------------
# 9. Context window around match
# ---------------------------------------------------------------------------

def test_context_window(search_projects_dir):
    """The context field contains text around the matched substring."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("unit tests", "-home-wiz-projects-myapp")

    assert len(results) == 1
    # Context should contain surrounding text
    assert "unit tests" in results[0].context.lower()


# ---------------------------------------------------------------------------
# 10. Message index is set
# ---------------------------------------------------------------------------

def test_message_index_set(search_projects_dir):
    """Results include the correct message_index for scroll navigation."""
    engine = SearchEngine(projects_root=search_projects_dir)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search(".env", "-home-wiz-projects-myapp")

    assert len(results) == 1
    assert results[0].message_index == 2  # Third message (index 2)


# ---------------------------------------------------------------------------
# 11. Meta messages are skipped
# ---------------------------------------------------------------------------

def test_meta_messages_skipped(tmp_path):
    """Meta messages (tool results) should not be searched."""
    projects = tmp_path / "projects"
    p1 = projects / "-home-wiz-test"
    p1.mkdir(parents=True)

    _write_session(p1 / "session-meta.jsonl", [
        _make_message("m1", "user", "user", "Read the secret file"),
        _make_message("m2", "user", "user", "secret_data_here", is_meta=True),
        _make_message("m3", "assistant", "assistant",
                      [{"type": "text", "text": "Done reading the file"}]),
    ])

    engine = SearchEngine(projects_root=projects)
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("secret_data_here", "-home-wiz-test")

    assert len(results) == 0


# ---------------------------------------------------------------------------
# 12. No projects_root set
# ---------------------------------------------------------------------------

def test_no_projects_root():
    """SearchEngine with no projects_root returns empty results."""
    engine = SearchEngine()
    results = []
    engine.results_ready.connect(lambda r: results.extend(r))

    engine.search("test", "some-project")

    assert len(results) == 0
