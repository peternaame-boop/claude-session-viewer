"""QAbstractListModel for the session list in the sidebar."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from claude_session_viewer.types import Session
from claude_session_viewer.utils.date_grouping import get_date_group


class SessionModel(QAbstractListModel):
    """Exposes a list of Sessions to QML with date-group sections."""

    SessionIdRole = Qt.UserRole + 1
    FirstMessageRole = Qt.UserRole + 2
    MessageCountRole = Qt.UserRole + 3
    RelativeTimeRole = Qt.UserRole + 4
    IsOngoingRole = Qt.UserRole + 5
    GitBranchRole = Qt.UserRole + 6
    DateGroupRole = Qt.UserRole + 7
    SectionRole = Qt.UserRole + 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: list[Session] = []

    def roleNames(self):
        return {
            self.SessionIdRole: b"sessionId",
            self.FirstMessageRole: b"firstMessage",
            self.MessageCountRole: b"messageCount",
            self.RelativeTimeRole: b"relativeTime",
            self.IsOngoingRole: b"isOngoing",
            self.GitBranchRole: b"gitBranch",
            self.DateGroupRole: b"dateGroup",
            self.SectionRole: b"section",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._sessions)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._sessions):
            return None

        session = self._sessions[index.row()]

        if role == self.SessionIdRole:
            return session.id
        elif role == self.FirstMessageRole:
            return session.first_message or "(empty session)"
        elif role == self.MessageCountRole:
            return session.message_count
        elif role == self.RelativeTimeRole:
            return self._format_relative_time(session.modified_at)
        elif role == self.IsOngoingRole:
            return session.is_ongoing
        elif role == self.GitBranchRole:
            return session.git_branch
        elif role in (self.DateGroupRole, self.SectionRole):
            group = get_date_group(session.modified_at)
            return group.value
        elif role == Qt.DisplayRole:
            return session.first_message or "(empty session)"
        return None

    def set_sessions(self, sessions: list[Session]):
        """Replace the entire session list."""
        self.beginResetModel()
        self._sessions = list(sessions)
        self.endResetModel()

    @staticmethod
    def _format_relative_time(timestamp: float) -> str:
        """Format a timestamp as a human-readable relative time."""
        import time
        diff = time.time() - timestamp
        if diff < 60:
            return "just now"
        elif diff < 3600:
            mins = int(diff / 60)
            return f"{mins}m ago"
        elif diff < 86400:
            hours = int(diff / 3600)
            return f"{hours}h ago"
        elif diff < 604800:
            days = int(diff / 86400)
            return f"{days}d ago"
        elif diff < 2592000:
            weeks = int(diff / 604800)
            return f"{weeks}w ago"
        else:
            months = int(diff / 2592000)
            return f"{months}mo ago"
