"""Multi-pane and tab management service."""

import uuid as uuid_mod
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, Slot, Property


@dataclass
class Tab:
    id: str
    session_id: str
    title: str
    project_id: str = ""


@dataclass
class Pane:
    id: str
    tabs: list[Tab] = field(default_factory=list)
    active_tab_id: str = ""

    @property
    def active_tab(self) -> Tab | None:
        for t in self.tabs:
            if t.id == self.active_tab_id:
                return t
        return self.tabs[0] if self.tabs else None


MAX_PANES = 4


class PaneManager(QObject):
    """Manages multi-pane tab layout state."""

    layout_changed = Signal()
    active_pane_changed = Signal()
    active_tab_changed = Signal(str)  # pane_id

    def __init__(self, parent=None):
        super().__init__(parent)
        initial_pane = Pane(id=str(uuid_mod.uuid4()))
        self._panes: list[Pane] = [initial_pane]
        self._active_pane_id: str = initial_pane.id

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def _get_active_pane_id(self) -> str:
        return self._active_pane_id

    activePaneId = Property(str, _get_active_pane_id, notify=active_pane_changed)

    def _get_pane_count(self) -> int:
        return len(self._panes)

    paneCount = Property(int, _get_pane_count, notify=layout_changed)

    # ------------------------------------------------------------------
    # Tab CRUD
    # ------------------------------------------------------------------

    @Slot(str, str, str)
    def open_tab(self, session_id: str, title: str, project_id: str = ""):
        """Open a session in a new tab in the active pane."""
        pane = self._get_pane(self._active_pane_id)
        if not pane:
            return

        # If session already open in this pane, activate it
        for tab in pane.tabs:
            if tab.session_id == session_id:
                pane.active_tab_id = tab.id
                self.active_tab_changed.emit(pane.id)
                return

        tab = Tab(
            id=str(uuid_mod.uuid4()),
            session_id=session_id,
            title=title,
            project_id=project_id,
        )
        pane.tabs.append(tab)
        pane.active_tab_id = tab.id
        self.layout_changed.emit()
        self.active_tab_changed.emit(pane.id)

    @Slot(str, str)
    def close_tab(self, pane_id: str, tab_id: str):
        """Close a tab. If pane becomes empty, remove it (unless last pane)."""
        pane = self._get_pane(pane_id)
        if not pane:
            return

        pane.tabs = [t for t in pane.tabs if t.id != tab_id]

        if not pane.tabs:
            if len(self._panes) > 1:
                self._panes = [p for p in self._panes if p.id != pane_id]
                self._active_pane_id = self._panes[0].id
                self.active_pane_changed.emit()
            else:
                pane.active_tab_id = ""
        elif pane.active_tab_id == tab_id:
            pane.active_tab_id = pane.tabs[-1].id

        self.layout_changed.emit()
        self.active_tab_changed.emit(pane_id)

    @Slot(str, str)
    def activate_tab(self, pane_id: str, tab_id: str):
        """Set the active tab in a pane."""
        pane = self._get_pane(pane_id)
        if pane:
            pane.active_tab_id = tab_id
            self._active_pane_id = pane_id
            self.active_pane_changed.emit()
            self.active_tab_changed.emit(pane_id)

    @Slot(str, int, int)
    def reorder_tab(self, pane_id: str, from_index: int, to_index: int):
        """Reorder a tab within a pane."""
        pane = self._get_pane(pane_id)
        if not pane or from_index == to_index:
            return
        if 0 <= from_index < len(pane.tabs) and 0 <= to_index < len(pane.tabs):
            tab = pane.tabs.pop(from_index)
            pane.tabs.insert(to_index, tab)
            self.layout_changed.emit()

    @Slot(str, str, str)
    def move_tab(self, from_pane_id: str, tab_id: str, to_pane_id: str):
        """Move a tab from one pane to another."""
        from_pane = self._get_pane(from_pane_id)
        to_pane = self._get_pane(to_pane_id)
        if not from_pane or not to_pane:
            return

        tab = None
        for t in from_pane.tabs:
            if t.id == tab_id:
                tab = t
                break
        if not tab:
            return

        from_pane.tabs = [t for t in from_pane.tabs if t.id != tab_id]
        to_pane.tabs.append(tab)
        to_pane.active_tab_id = tab.id

        # Clean up empty from_pane
        if not from_pane.tabs and len(self._panes) > 1:
            self._panes = [p for p in self._panes if p.id != from_pane_id]
        elif from_pane.active_tab_id == tab_id and from_pane.tabs:
            from_pane.active_tab_id = from_pane.tabs[-1].id

        self._active_pane_id = to_pane.id
        self.layout_changed.emit()
        self.active_pane_changed.emit()

    # ------------------------------------------------------------------
    # Pane management
    # ------------------------------------------------------------------

    @Slot(result=str)
    def split_pane(self) -> str:
        """Split the active pane, creating a new empty pane. Returns new pane ID."""
        if len(self._panes) >= MAX_PANES:
            return ""

        new_pane = Pane(id=str(uuid_mod.uuid4()))
        self._panes.append(new_pane)
        self.layout_changed.emit()
        return new_pane.id

    @Slot(str)
    def remove_pane(self, pane_id: str):
        """Remove a pane, merging its tabs into the previous pane."""
        if len(self._panes) <= 1:
            return

        pane = self._get_pane(pane_id)
        if not pane:
            return

        # Find target pane to merge tabs into
        idx = next(i for i, p in enumerate(self._panes) if p.id == pane_id)
        target_idx = idx - 1 if idx > 0 else 1
        target = self._panes[target_idx]

        # Merge tabs
        target.tabs.extend(pane.tabs)
        if pane.tabs and not target.active_tab_id:
            target.active_tab_id = pane.tabs[0].id

        self._panes = [p for p in self._panes if p.id != pane_id]
        if self._active_pane_id == pane_id:
            self._active_pane_id = target.id
            self.active_pane_changed.emit()

        self.layout_changed.emit()

    @Slot(str)
    def set_active_pane(self, pane_id: str):
        """Set the active pane."""
        if self._get_pane(pane_id) and self._active_pane_id != pane_id:
            self._active_pane_id = pane_id
            self.active_pane_changed.emit()

    # ------------------------------------------------------------------
    # Query methods for QML
    # ------------------------------------------------------------------

    @Slot(result=list)
    def get_layout(self) -> list[dict]:
        """Return the full pane/tab layout for QML."""
        return [
            {
                "paneId": pane.id,
                "activeTabId": pane.active_tab_id,
                "tabs": [
                    {
                        "tabId": tab.id,
                        "sessionId": tab.session_id,
                        "title": tab.title,
                        "projectId": tab.project_id,
                    }
                    for tab in pane.tabs
                ],
            }
            for pane in self._panes
        ]

    @Slot(str, result=str)
    def get_active_session_id(self, pane_id: str) -> str:
        """Get the session ID of the active tab in a pane."""
        pane = self._get_pane(pane_id)
        if pane and pane.active_tab:
            return pane.active_tab.session_id
        return ""

    @Slot(str, result=list)
    def get_tabs(self, pane_id: str) -> list[dict]:
        """Get tabs for a specific pane."""
        pane = self._get_pane(pane_id)
        if not pane:
            return []
        return [
            {
                "tabId": tab.id,
                "sessionId": tab.session_id,
                "title": tab.title,
                "projectId": tab.project_id,
                "active": tab.id == pane.active_tab_id,
            }
            for tab in pane.tabs
        ]

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    @Slot()
    def next_tab(self):
        """Activate the next tab in the active pane (Ctrl+Tab)."""
        pane = self._get_pane(self._active_pane_id)
        if not pane or len(pane.tabs) < 2:
            return
        idx = next((i for i, t in enumerate(pane.tabs) if t.id == pane.active_tab_id), 0)
        new_idx = (idx + 1) % len(pane.tabs)
        pane.active_tab_id = pane.tabs[new_idx].id
        self.active_tab_changed.emit(pane.id)

    @Slot()
    def prev_tab(self):
        """Activate the previous tab in the active pane (Ctrl+Shift+Tab)."""
        pane = self._get_pane(self._active_pane_id)
        if not pane or len(pane.tabs) < 2:
            return
        idx = next((i for i, t in enumerate(pane.tabs) if t.id == pane.active_tab_id), 0)
        new_idx = (idx - 1) % len(pane.tabs)
        pane.active_tab_id = pane.tabs[new_idx].id
        self.active_tab_changed.emit(pane.id)

    @Slot()
    def close_active_tab(self):
        """Close the active tab in the active pane (Ctrl+W)."""
        pane = self._get_pane(self._active_pane_id)
        if pane and pane.active_tab_id:
            self.close_tab(pane.id, pane.active_tab_id)

    @Slot(int)
    def activate_tab_by_index(self, index: int):
        """Activate tab by 0-based index in the active pane (Ctrl+1-9)."""
        pane = self._get_pane(self._active_pane_id)
        if pane and 0 <= index < len(pane.tabs):
            pane.active_tab_id = pane.tabs[index].id
            self.active_tab_changed.emit(pane.id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_pane(self, pane_id: str) -> Pane | None:
        for p in self._panes:
            if p.id == pane_id:
                return p
        return None
