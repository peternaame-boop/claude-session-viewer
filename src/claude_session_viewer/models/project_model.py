"""QAbstractListModel for the project sidebar selector."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot

from claude_session_viewer.types import Project


class ProjectModel(QAbstractListModel):
    """Exposes a list of Projects to QML."""

    ProjectIdRole = Qt.UserRole + 1
    ProjectPathRole = Qt.UserRole + 2
    ProjectNameRole = Qt.UserRole + 3
    SessionCountRole = Qt.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list[Project] = []

    def roleNames(self):
        return {
            self.ProjectIdRole: b"projectId",
            self.ProjectPathRole: b"projectPath",
            self.ProjectNameRole: b"projectName",
            self.SessionCountRole: b"sessionCount",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._projects)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._projects):
            return None

        project = self._projects[index.row()]

        if role == self.ProjectIdRole:
            return project.id
        elif role == self.ProjectPathRole:
            return project.path
        elif role == self.ProjectNameRole:
            return project.name
        elif role == self.SessionCountRole:
            return project.session_count
        elif role == Qt.DisplayRole:
            return project.name
        return None

    def set_projects(self, projects: list[Project]):
        """Replace the entire project list."""
        self.beginResetModel()
        self._projects = list(projects)
        self.endResetModel()

    @Slot(int, result=str)
    def get_project_id(self, index: int) -> str:
        """Get project ID by index (for QML ComboBox)."""
        if 0 <= index < len(self._projects):
            return self._projects[index].id
        return ""
