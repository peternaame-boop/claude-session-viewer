"""Integration tests for the application entry point."""

import os
import sys

import pytest


@pytest.fixture(autouse=True)
def offscreen_platform():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestAppImports:
    def test_app_module_importable(self):
        from claude_session_viewer import app
        assert hasattr(app, "run")

    def test_all_singletons_creatable(self, qapp):
        from claude_session_viewer.services.session_manager import SessionManager
        from claude_session_viewer.models.project_model import ProjectModel
        from claude_session_viewer.models.session_model import SessionModel
        from claude_session_viewer.models.conversation_model import ConversationModel

        manager = SessionManager()
        pm = ProjectModel()
        sm = SessionModel()
        cm = ConversationModel()

        assert manager is not None
        assert pm is not None
        assert sm is not None
        assert cm is not None
        manager.cleanup()

    def test_qml_file_exists(self):
        from pathlib import Path
        qml_dir = Path(__file__).parent.parent / "src" / "claude_session_viewer" / "qml"
        main_qml = qml_dir / "Main.qml"
        assert main_qml.exists(), f"Main.qml not found at {main_qml}"
        assert (qml_dir / "ChatHistoryView.qml").exists()
        assert (qml_dir / "components" / "chat" / "UserGroup.qml").exists()
        assert (qml_dir / "components" / "chat" / "AIGroup.qml").exists()
        assert (qml_dir / "components" / "chat" / "SystemGroup.qml").exists()
        assert (qml_dir / "components" / "chat" / "CompactGroup.qml").exists()
        assert (qml_dir / "components" / "tools" / "ToolCard.qml").exists()
