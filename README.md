# Claude Session Viewer

Native KDE Plasma 6 desktop application that reads Claude Code session logs from `~/.claude/projects/` and presents them in a structured, visual interface.

## What It Does

Claude Code stores session data as JSONL files. This viewer reconstructs every interaction — file reads, edits, diffs, command executions, tool calls, token usage — and displays them with specialized renderers instead of raw JSON.

### Features

- **Full session reconstruction** from raw JSONL logs with message classification
- **Cross-session search** via Ctrl+K command palette
- **Multi-pane tabbed interface** (up to 4 panes, drag tabs between them)
- **Desktop notifications** with configurable regex triggers (`.env` access, errors, token thresholds)
- **SSH/SFTP remote viewing** for sessions on remote servers
- **Git integration** (branch detection, worktree support, remote URL resolution)
- **Syntax-highlighted diffs** via KSyntaxHighlighting
- **Context analysis** (file access tracking, tool usage patterns)
- **Subagent detection** and hierarchy visualization
- **Live file watching** with inotify-based auto-refresh

### Why Not claude-devtools?

[claude-devtools](https://github.com/matt1398/claude-devtools) does the same thing but runs Electron (200-400MB RAM for a log viewer). This app targets 50-80MB using native Qt/KDE.

## Requirements

- KDE Plasma 6 / Qt 6
- Python 3.12+
- PySide6 6.10+
- Kirigami 6.x
- KSyntaxHighlighting

## Installation

### From source

```bash
pip install -e ".[dev]"
claude-session-viewer
```

### Arch Linux (PKGBUILD)

```bash
makepkg -si
```

## Running

```bash
# Direct
claude-session-viewer

# Module
python -m claude_session_viewer
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+K | Command palette (search) |
| Ctrl+B | Toggle sidebar |
| Ctrl+W | Close active tab |
| Ctrl+Tab | Next tab |
| Ctrl+Shift+Tab | Previous tab |
| Ctrl+\\ | Split pane |
| Ctrl+1-9 | Switch to tab N |
| Ctrl+R / F5 | Refresh |

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
src/claude_session_viewer/
  types/          # Dataclasses (messages, sessions, chunks, notifications, context)
  utils/          # Pure functions (parsing, sanitization, validation, diffing)
  services/       # QObject services (session manager, search, notifications, SSH)
  models/         # QAbstractListModel subclasses for QML binding
  qml/            # QML UI (Main.qml + components/)
```

## Changelog

### v1.0.0 (2026-02-14)
- Initial release
- Phase 1: JSONL parsing, message classification, content sanitization
- Phase 2: Session management, metadata caching, file watching
- Phase 3: QML models, conversation view, project/session list
- Phase 4: Context analysis, subagent detection, diff generation
- Phase 5: Cross-session search, desktop notifications, command palette
- Phase 6: Multi-pane tabbed interface with drag-and-drop
- Phase 7: SSH/SFTP, git resolver, config manager, settings UI
- Phase 8: Full test suite, packaging, desktop integration

## License

MIT
