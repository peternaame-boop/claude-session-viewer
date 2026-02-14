"""Tests for claude_session_viewer.services.pane_manager."""

import pytest

from claude_session_viewer.services.pane_manager import PaneManager, MAX_PANES


@pytest.fixture
def pm(qapp):
    return PaneManager()


# ---------------------------------------------------------------------------
# 1. Initial state
# ---------------------------------------------------------------------------

def test_initial_state(pm):
    """Manager starts with one empty pane."""
    layout = pm.get_layout()
    assert len(layout) == 1
    assert layout[0]["tabs"] == []


# ---------------------------------------------------------------------------
# 2. Open tab
# ---------------------------------------------------------------------------

def test_open_tab(pm):
    """Opening a tab adds it to the active pane."""
    pm.open_tab("session-1", "Test Session", "project-1")
    layout = pm.get_layout()
    assert len(layout[0]["tabs"]) == 1
    assert layout[0]["tabs"][0]["sessionId"] == "session-1"


# ---------------------------------------------------------------------------
# 3. Open duplicate tab activates existing
# ---------------------------------------------------------------------------

def test_open_duplicate_activates(pm):
    """Opening the same session ID doesn't create a duplicate tab."""
    pm.open_tab("session-1", "Test", "project-1")
    pm.open_tab("session-2", "Test 2", "project-1")
    pm.open_tab("session-1", "Test", "project-1")
    layout = pm.get_layout()
    assert len(layout[0]["tabs"]) == 2
    assert layout[0]["activeTabId"] == layout[0]["tabs"][0]["tabId"]


# ---------------------------------------------------------------------------
# 4. Close tab
# ---------------------------------------------------------------------------

def test_close_tab(pm):
    """Closing a tab removes it from the pane."""
    pm.open_tab("session-1", "Test", "project-1")
    pm.open_tab("session-2", "Test 2", "project-1")
    layout = pm.get_layout()
    tab_id = layout[0]["tabs"][0]["tabId"]
    pane_id = layout[0]["paneId"]

    pm.close_tab(pane_id, tab_id)
    layout = pm.get_layout()
    assert len(layout[0]["tabs"]) == 1


# ---------------------------------------------------------------------------
# 5. Split pane
# ---------------------------------------------------------------------------

def test_split_pane(pm):
    """Splitting creates a new empty pane."""
    pm.split_pane()
    layout = pm.get_layout()
    assert len(layout) == 2


# ---------------------------------------------------------------------------
# 6. Max panes enforced
# ---------------------------------------------------------------------------

def test_max_panes(pm):
    """Cannot exceed MAX_PANES."""
    for _ in range(MAX_PANES + 2):
        pm.split_pane()
    layout = pm.get_layout()
    assert len(layout) == MAX_PANES


# ---------------------------------------------------------------------------
# 7. Remove pane merges tabs
# ---------------------------------------------------------------------------

def test_remove_pane_merges(pm):
    """Removing a pane merges its tabs into the adjacent pane."""
    pm.open_tab("session-1", "Test", "project-1")
    new_pane_id = pm.split_pane()
    pm.set_active_pane(new_pane_id)
    pm.open_tab("session-2", "Test 2", "project-1")

    pm.remove_pane(new_pane_id)
    layout = pm.get_layout()
    assert len(layout) == 1
    assert len(layout[0]["tabs"]) == 2


# ---------------------------------------------------------------------------
# 8. Close tab in last pane keeps pane
# ---------------------------------------------------------------------------

def test_close_last_tab_keeps_pane(pm):
    """Closing the only tab in the only pane leaves an empty pane."""
    pm.open_tab("session-1", "Test", "project-1")
    layout = pm.get_layout()
    pane_id = layout[0]["paneId"]
    tab_id = layout[0]["tabs"][0]["tabId"]

    pm.close_tab(pane_id, tab_id)
    layout = pm.get_layout()
    assert len(layout) == 1
    assert len(layout[0]["tabs"]) == 0


# ---------------------------------------------------------------------------
# 9. Next/prev tab cycling
# ---------------------------------------------------------------------------

def test_next_prev_tab(pm):
    """next_tab and prev_tab cycle through tabs."""
    pm.open_tab("s1", "T1", "p1")
    pm.open_tab("s2", "T2", "p1")
    pm.open_tab("s3", "T3", "p1")

    # Active should be s3 (last opened)
    pane_id = pm.get_layout()[0]["paneId"]
    assert pm.get_active_session_id(pane_id) == "s3"

    pm.next_tab()
    assert pm.get_active_session_id(pane_id) == "s1"  # wraps around

    pm.prev_tab()
    assert pm.get_active_session_id(pane_id) == "s3"  # wraps back


# ---------------------------------------------------------------------------
# 10. Activate tab by index
# ---------------------------------------------------------------------------

def test_activate_tab_by_index(pm):
    """activate_tab_by_index switches to the correct tab."""
    pm.open_tab("s1", "T1", "p1")
    pm.open_tab("s2", "T2", "p1")
    pm.open_tab("s3", "T3", "p1")

    pm.activate_tab_by_index(0)
    pane_id = pm.get_layout()[0]["paneId"]
    assert pm.get_active_session_id(pane_id) == "s1"

    pm.activate_tab_by_index(2)
    assert pm.get_active_session_id(pane_id) == "s3"


# ---------------------------------------------------------------------------
# 11. Move tab between panes
# ---------------------------------------------------------------------------

def test_move_tab(pm):
    """Moving a tab transfers it to another pane."""
    pm.open_tab("s1", "T1", "p1")
    pm.open_tab("s2", "T2", "p1")
    new_pane_id = pm.split_pane()

    layout = pm.get_layout()
    from_pane_id = layout[0]["paneId"]
    tab_id = layout[0]["tabs"][0]["tabId"]

    pm.move_tab(from_pane_id, tab_id, new_pane_id)
    layout = pm.get_layout()

    # Source pane has 1 tab, target has 1
    pane_tabs = {p["paneId"]: p["tabs"] for p in layout}
    assert len(pane_tabs[from_pane_id]) == 1
    assert len(pane_tabs[new_pane_id]) == 1


# ---------------------------------------------------------------------------
# 12. Reorder tabs
# ---------------------------------------------------------------------------

def test_reorder_tab(pm):
    """Reordering changes tab position within a pane."""
    pm.open_tab("s1", "T1", "p1")
    pm.open_tab("s2", "T2", "p1")
    pm.open_tab("s3", "T3", "p1")

    pane_id = pm.get_layout()[0]["paneId"]
    pm.reorder_tab(pane_id, 0, 2)

    tabs = pm.get_tabs(pane_id)
    assert tabs[2]["sessionId"] == "s1"
