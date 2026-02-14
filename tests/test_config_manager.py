"""Tests for claude_session_viewer.services.config_manager."""

import pytest

from claude_session_viewer.services.config_manager import ConfigManager


@pytest.fixture
def config(qapp, tmp_path):
    """Create a ConfigManager with isolated QSettings."""
    from PySide6.QtCore import QSettings
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "config"))
    return ConfigManager()


# ---------------------------------------------------------------------------
# 1. Get default string
# ---------------------------------------------------------------------------

def test_default_string(config):
    """Unknown key returns default from DEFAULTS dict."""
    val = config.get_string("general/sessionDir")
    assert "claude" in val.lower() or val == "~/.claude/projects"


# ---------------------------------------------------------------------------
# 2. Set and get string
# ---------------------------------------------------------------------------

def test_set_get_string(config):
    """Setting a string value persists it."""
    config.set_string("general/sessionDir", "/custom/path")
    assert config.get_string("general/sessionDir") == "/custom/path"


# ---------------------------------------------------------------------------
# 3. Set and get int
# ---------------------------------------------------------------------------

def test_set_get_int(config):
    """Setting an int value persists it."""
    config.set_int("general/maxRecentSessions", 100)
    assert config.get_int("general/maxRecentSessions") == 100


# ---------------------------------------------------------------------------
# 4. Set and get bool
# ---------------------------------------------------------------------------

def test_set_get_bool(config):
    """Setting a bool value persists it."""
    config.set_bool("general/showCosts", False)
    assert config.get_bool("general/showCosts") is False


# ---------------------------------------------------------------------------
# 5. Settings changed signal
# ---------------------------------------------------------------------------

def test_settings_changed_signal(config):
    """settings_changed emits the key that was changed."""
    keys = []
    config.settings_changed.connect(lambda k: keys.append(k))
    config.set_string("test/key", "value")
    assert keys == ["test/key"]


# ---------------------------------------------------------------------------
# 6. SSH profile CRUD
# ---------------------------------------------------------------------------

def test_ssh_profile_crud(config):
    """SSH profiles can be saved, listed, and removed."""
    config.save_ssh_profile("server1", "host1.example.com", 22, "user1", "~/.ssh/id_ed25519")
    profiles = config.get_ssh_profiles()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "server1"

    config.save_ssh_profile("server2", "host2.example.com", 2222, "user2", "")
    profiles = config.get_ssh_profiles()
    assert len(profiles) == 2

    config.remove_ssh_profile("server1")
    profiles = config.get_ssh_profiles()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "server2"


# ---------------------------------------------------------------------------
# 7. SSH profile update
# ---------------------------------------------------------------------------

def test_ssh_profile_update(config):
    """Saving a profile with the same name updates it."""
    config.save_ssh_profile("server1", "old.host", 22, "user", "")
    config.save_ssh_profile("server1", "new.host", 2222, "user2", "/key")
    profiles = config.get_ssh_profiles()
    assert len(profiles) == 1
    assert profiles[0]["host"] == "new.host"
    assert profiles[0]["port"] == 2222
