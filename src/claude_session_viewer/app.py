"""Application entry point — QML engine setup and model registration."""

import os
import sys
import signal
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QLocalSocket, QLocalServer

from claude_session_viewer.services.session_manager import SessionManager
from claude_session_viewer.services.search_engine import SearchEngine
from claude_session_viewer.services.notification_manager import NotificationManager
from claude_session_viewer.services.pane_manager import PaneManager
from claude_session_viewer.services.ssh_manager import SshManager
from claude_session_viewer.services.config_manager import ConfigManager
from claude_session_viewer.models.project_model import ProjectModel
from claude_session_viewer.models.session_model import SessionModel
from claude_session_viewer.models.conversation_model import ConversationModel
from claude_session_viewer.models.search_result_model import SearchResultModel

QML_DIR = Path(__file__).parent / "qml"
SOCKET_NAME = "claude-session-viewer-instance"


def _check_single_instance() -> QLocalServer | None:
    """Enforce single instance via QLocalSocket. Returns server if we're the first instance."""
    socket = QLocalSocket()
    socket.connectToServer(SOCKET_NAME)
    if socket.waitForConnected(500):
        # Another instance is running
        socket.close()
        return None

    server = QLocalServer()
    server.removeServer(SOCKET_NAME)
    server.listen(SOCKET_NAME)
    return server


def run() -> int:
    """Launch the application."""
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "org.kde.desktop"

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Claude Session Viewer")
    app.setOrganizationName("claude-session-viewer")
    app.setOrganizationDomain("claude.local")
    app.setDesktopFileName("org.kde.claudesessionviewer")

    # Single instance check
    instance_server = _check_single_instance()
    if instance_server is None:
        print("Another instance is already running.", file=sys.stderr)
        return 0

    # Allow Ctrl+C to kill the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    engine = QQmlApplicationEngine()

    # Add Kirigami import path (system-wide Qt6 QML modules)
    engine.addImportPath("/usr/lib/qt6/qml")

    # Create backend objects
    manager = SessionManager()
    project_model = ProjectModel()
    session_model = SessionModel()
    conversation_model = ConversationModel()
    search_engine = SearchEngine()
    search_result_model = SearchResultModel()
    notification_manager = NotificationManager()
    pane_manager = PaneManager()
    ssh_manager = SshManager()
    config_manager = ConfigManager()

    # Wire signals: manager -> models
    manager.projects_loaded.connect(
        lambda: project_model.set_projects(manager.get_projects())
    )
    manager.sessions_loaded.connect(
        lambda pid: session_model.set_sessions(manager.get_sessions(pid))
    )
    manager.conversation_loaded.connect(
        lambda sid: conversation_model.set_chunks(manager.get_chunks(sid))
    )

    # Wire search engine: results -> model
    search_engine.results_ready.connect(search_result_model.set_results)

    # Wire session file changes -> notification manager
    manager.session_file_changed.connect(notification_manager.check_file)

    # Set search engine projects root when projects are scanned
    manager.projects_loaded.connect(
        lambda: search_engine.set_projects_root(manager._projects_root)
    )

    # Expose backend objects to QML via context properties.
    # Using setContextProperty avoids qmlRegisterSingletonInstance which triggers
    # PySide6's bundled Qt type system, causing ABI conflicts with system Kirigami.
    ctx = engine.rootContext()
    ctx.setContextProperty("SessionManager", manager)
    ctx.setContextProperty("ProjectModel", project_model)
    ctx.setContextProperty("SessionModel", session_model)
    ctx.setContextProperty("ConversationModel", conversation_model)
    ctx.setContextProperty("SearchEngine", search_engine)
    ctx.setContextProperty("SearchResultModel", search_result_model)
    ctx.setContextProperty("NotificationManager", notification_manager)
    ctx.setContextProperty("PaneManager", pane_manager)
    ctx.setContextProperty("SshManager", ssh_manager)
    ctx.setContextProperty("ConfigManager", config_manager)

    # Load QML
    qml_file = QML_DIR / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        return 1

    # Initial project scan
    manager.scan_projects()

    ret = app.exec()
    manager.cleanup()
    ssh_manager.cleanup()
    instance_server.close()
    return ret
