# Claude Session Viewer

Native KDE Plasma 6 desktop application that reads Claude Code session logs from `~/.claude/projects/` and presents them in a structured, visual interface.

## What It Does

Claude Code stores session data as JSONL files. This viewer reconstructs every interaction — file reads, edits, diffs, command executions, tool calls, token usage — and displays them with specialized renderers instead of raw JSON.

### Features

- **Full session reconstruction** from raw JSONL logs with message classification
- **Compact message view** — all rows collapsed by default with preview text, expandable on click
- **Virtual pagination** — handles 9000+ message sessions without crashing (loads 200 chunks at a time)
- **Live tailing** — incremental parsing of active sessions (only reads new bytes, not full re-parse)
- **Active session detection** — green dot on sessions being actively written to, with configurable timeout
- **Follow-active mode** — auto-switch to whichever session Claude Code is currently writing to
- **Cross-session search** via Ctrl+K command palette
- **Multi-pane tabbed interface** (up to 4 panes, drag tabs between them)
- **Desktop notifications** with configurable regex triggers (`.env` access, errors, token thresholds)
- **SSH/SFTP remote viewing** for sessions on remote servers
- **Git integration** (branch detection, worktree support, remote URL resolution)
- **Syntax-highlighted diffs** via KSyntaxHighlighting
- **Context analysis** (file access tracking, tool usage patterns, token breakdown)
- **Subagent detection** and hierarchy visualization
- **Background loading** — large sessions parsed in a worker thread, UI stays responsive

### Why Not claude-devtools?

[claude-devtools](https://github.com/matt1398/claude-devtools) does the same thing but runs Electron (200-400MB RAM for a log viewer). This app targets 50-80MB using native Qt/KDE.

## Screenshots

*(Coming soon)*

## Requirements

- KDE Plasma 6 / Qt 6
- Python 3.12+
- PySide6 6.10+
- Kirigami 6.x
- KSyntaxHighlighting

## Installation

### From source

```bash
git clone https://github.com/peternaame-boop/claude-session-viewer.git
cd claude-session-viewer
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
# Full suite (372 tests)
pytest tests/ -v

# With coverage
pytest tests/ --cov=claude_session_viewer --cov-report=term-missing
```

## Architecture

```
src/claude_session_viewer/
  app.py            # Application bootstrap, QML engine setup, signal wiring
  types/            # Dataclasses (messages, sessions, chunks, notifications, context)
  utils/            # Pure functions (parsing, sanitization, validation, diffing)
  services/         # QObject services:
    session_manager.py      # Central orchestrator, message cache, byte offset tracking
    file_watcher.py         # inotify-based auto-refresh + project dir watching
    search_engine.py        # Cross-session full-text search
    notification_manager.py # D-Bus notifications with regex triggers
    ssh_manager.py          # SSH/SFTP remote session access
    config_manager.py       # QSettings-based configuration
    pane_manager.py         # Multi-pane tab management
    chunk_builder.py        # JSONL message grouping into conversation chunks
    context_analyzer.py     # File access tracking, tool usage patterns
    subagent_resolver.py    # Subagent detection and hierarchy
    git_resolver.py         # Branch detection, worktree support
    tool_linker.py          # Tool call/result pairing
    jsonl_parser.py         # Core JSONL streaming parser with offset support
    metadata_cache.py       # Session metadata caching
  models/           # QAbstractListModel subclasses for QML binding:
    conversation_model.py   # Virtual pagination, incremental updates
    session_model.py        # Session list with live activity indicators
    project_model.py        # Project grouping
    search_result_model.py  # Search results
  qml/              # QML UI (Main.qml + 25 components)
    components/
      chat/       # UserGroup, AIGroup, SystemGroup, CompactGroup
      tools/      # ToolCard, SubagentItem + 6 specialized viewers
      context/    # ContextBadge, SessionContextPanel, TokenUsagePopover
      layout/     # PaneContainer, PaneView, TabBarView
      common/     # CopyButton
```

## How It Works

1. **JSONL Parsing** — Sessions are streamed from `~/.claude/projects/*/sessions/*.jsonl` using `orjson` for fast parsing. Byte offsets are tracked for incremental re-reads.

2. **Message Classification** — Raw messages are classified into types (user, assistant, system, tool_call, tool_result, etc.) and paired into tool executions.

3. **Chunk Building** — Messages are grouped into conversation chunks (user turn, AI response, system event, context compaction) for display.

4. **Virtual Pagination** — Only the last 200 chunks are exposed to QML. Earlier chunks load on demand ("Load earlier messages" button). This keeps the UI responsive even for sessions with thousands of messages.

5. **Live Tailing** — When a session file changes, only new bytes are parsed (via stored byte offset), new messages appended to cache, and chunks rebuilt in-memory. The QML model receives minimal updates (dataChanged for modified chunks, insertRows for new ones).

6. **Active Detection** — All project directories are watched via inotify. When a session file is modified, it's marked active (green dot). After 30 seconds of inactivity, the dot disappears.

## Changelog

### v1.1.0 (2026-02-14)
- Live tailing with incremental JSONL parsing (byte offset tracking)
- Active session detection with green dot indicators
- Follow-active mode (auto-switch to session being written to)
- Virtual pagination for large sessions (200 chunks at a time)
- Background worker thread for conversation loading
- Compact collapsed message view with lazy expansion
- Settings page stacking fix
- 4 new test files, 372 total tests passing

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
