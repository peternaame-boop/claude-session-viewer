"""Application configuration manager wrapping QSettings."""

import json
import logging

from PySide6.QtCore import QObject, Signal, Slot, Property, QSettings

logger = logging.getLogger(__name__)

# Default values
DEFAULTS = {
    "general/sessionDir": "~/.claude/projects",
    "general/maxRecentSessions": 50,
    "general/showCosts": True,
    "general/autoRefresh": True,
    "appearance/codeFontSize": 10,
    "appearance/wordWrap": False,
    "appearance/compactMode": False,
    "notifications/enabled": True,
    "notifications/sound": True,
    "ssh/pollInterval": 3000,
    "ssh/timeout": 10,
    "advanced/debugLogging": False,
}


class ConfigManager(QObject):
    """Centralized application settings with QML property bindings."""

    settings_changed = Signal(str)  # key

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings()

    @Slot(str, result=str)
    def get_string(self, key: str) -> str:
        return str(self._settings.value(key, DEFAULTS.get(key, "")))

    @Slot(str, result=int)
    def get_int(self, key: str) -> int:
        val = self._settings.value(key, DEFAULTS.get(key, 0))
        try:
            return int(val)
        except (ValueError, TypeError):
            return DEFAULTS.get(key, 0)

    @Slot(str, result=bool)
    def get_bool(self, key: str) -> bool:
        val = self._settings.value(key, DEFAULTS.get(key, False))
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    @Slot(str, str)
    def set_string(self, key: str, value: str):
        self._settings.setValue(key, value)
        self.settings_changed.emit(key)

    @Slot(str, int)
    def set_int(self, key: str, value: int):
        self._settings.setValue(key, value)
        self.settings_changed.emit(key)

    @Slot(str, bool)
    def set_bool(self, key: str, value: bool):
        self._settings.setValue(key, value)
        self.settings_changed.emit(key)

    # SSH profile persistence
    @Slot(result=list)
    def get_ssh_profiles(self) -> list[dict]:
        """Load saved SSH profiles."""
        raw = self._settings.value("ssh/profiles", "[]")
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @Slot(str, str, int, str, str)
    def save_ssh_profile(self, name: str, host: str, port: int, username: str, key_path: str):
        """Save or update an SSH profile."""
        profiles = self.get_ssh_profiles()
        # Update existing or add new
        for p in profiles:
            if p.get("name") == name:
                p.update({"host": host, "port": port, "username": username, "keyPath": key_path})
                break
        else:
            profiles.append({
                "name": name, "host": host, "port": port,
                "username": username, "keyPath": key_path,
            })
        self._settings.setValue("ssh/profiles", json.dumps(profiles))
        self.settings_changed.emit("ssh/profiles")

    @Slot(str)
    def remove_ssh_profile(self, name: str):
        """Remove an SSH profile by name."""
        profiles = [p for p in self.get_ssh_profiles() if p.get("name") != name]
        self._settings.setValue("ssh/profiles", json.dumps(profiles))
        self.settings_changed.emit("ssh/profiles")

    @Slot()
    def clear_cache(self):
        """Clear the application cache directory."""
        import shutil
        from pathlib import Path
        cache_dir = Path.home() / ".cache" / "claude-session-viewer"
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
