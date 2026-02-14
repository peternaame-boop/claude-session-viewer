"""QAbstractListModel for search results displayed in the command palette."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot

from claude_session_viewer.types.notifications import SearchResult


class SearchResultModel(QAbstractListModel):
    """Exposes search results to QML."""

    SessionIdRole = Qt.UserRole + 1
    ProjectIdRole = Qt.UserRole + 2
    SessionTitleRole = Qt.UserRole + 3
    MatchedTextRole = Qt.UserRole + 4
    ContextRole = Qt.UserRole + 5
    MessageTypeRole = Qt.UserRole + 6
    TimestampRole = Qt.UserRole + 7
    MessageIndexRole = Qt.UserRole + 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[SearchResult] = []

    def roleNames(self):
        return {
            self.SessionIdRole: b"sessionId",
            self.ProjectIdRole: b"projectId",
            self.SessionTitleRole: b"sessionTitle",
            self.MatchedTextRole: b"matchedText",
            self.ContextRole: b"context",
            self.MessageTypeRole: b"messageType",
            self.TimestampRole: b"timestamp",
            self.MessageIndexRole: b"messageIndex",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._results)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._results):
            return None

        result = self._results[index.row()]

        if role == self.SessionIdRole:
            return result.session_id
        elif role == self.ProjectIdRole:
            return result.project_id
        elif role == self.SessionTitleRole:
            return result.session_title
        elif role == self.MatchedTextRole:
            return result.matched_text
        elif role == self.ContextRole:
            return result.context
        elif role == self.MessageTypeRole:
            return result.message_type
        elif role == self.TimestampRole:
            return result.timestamp
        elif role == self.MessageIndexRole:
            return result.message_index
        return None

    def set_results(self, results: list[SearchResult]):
        """Replace the entire results list."""
        self.beginResetModel()
        self._results = list(results)
        self.endResetModel()

    @Slot()
    def clear(self):
        """Clear all search results."""
        self.beginResetModel()
        self._results = []
        self.endResetModel()
