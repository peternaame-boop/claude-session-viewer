"""Tests for claude_session_viewer.services.file_watcher."""

import os
import time

import pytest

from claude_session_viewer.services.file_watcher import FileWatcher


@pytest.fixture
def watcher(qapp):
    w = FileWatcher()
    yield w
    w.stop()


class TestFileWatcherStartStop:
    def test_start_adds_directory(self, watcher, tmp_path):
        watcher.start(str(tmp_path))
        assert str(tmp_path) in watcher._watcher.directories()

    def test_stop_clears_everything(self, watcher, tmp_path):
        watcher.start(str(tmp_path))
        f = tmp_path / "test.jsonl"
        f.write_text("{}")
        watcher.watch_session(str(f))
        watcher.stop()
        assert len(watcher._watcher.directories()) == 0
        assert len(watcher._watcher.files()) == 0
        assert len(watcher._watched_sessions) == 0


class TestFileWatcherSession:
    def test_watch_unwatch_session(self, watcher, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text("{}")
        watcher.watch_session(str(f))
        assert str(f) in watcher._watched_sessions
        watcher.unwatch_session(str(f))
        assert str(f) not in watcher._watched_sessions

    def test_double_watch_no_duplicate(self, watcher, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text("{}")
        watcher.watch_session(str(f))
        watcher.watch_session(str(f))
        assert len(watcher._watched_sessions) == 1


class TestFileWatcherSignals:
    def test_session_changed_signal_emitted(self, watcher, qapp, tmp_path):
        """Test that modifying a watched file emits session_changed."""
        f = tmp_path / "session.jsonl"
        f.write_text("{}")
        watcher.watch_session(str(f))

        received = []
        watcher.session_changed.connect(lambda path: received.append(path))

        # Modify the file and process events
        time.sleep(0.05)
        f.write_text('{"updated": true}')

        # Process Qt events to trigger file watcher
        for _ in range(20):
            qapp.processEvents()
            time.sleep(0.05)

        assert len(received) >= 1
        assert received[0] == str(f)
