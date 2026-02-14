"""QAbstractListModel for conversation chunks displayed in the chat view."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from claude_session_viewer.types import Chunk, ChunkType, ToolExecution
from claude_session_viewer.utils.content_sanitizer import sanitize_content, extract_user_text
from claude_session_viewer.utils.diff_generator import (
    compute_inline_diff,
    get_syntax_definition,
    get_file_extension,
    strip_line_numbers,
)


class ConversationModel(QAbstractListModel):
    """Exposes conversation Chunks to QML."""

    ChunkIdRole = Qt.UserRole + 1
    ChunkTypeRole = Qt.UserRole + 2
    UserTextRole = Qt.UserRole + 3
    AiTextRole = Qt.UserRole + 4
    SystemTextRole = Qt.UserRole + 5
    StatusRole = Qt.UserRole + 6
    ToolCountRole = Qt.UserRole + 7
    ToolExecutionsRole = Qt.UserRole + 8
    TokenCountRole = Qt.UserRole + 9
    DurationRole = Qt.UserRole + 10
    CostRole = Qt.UserRole + 11
    ModelNameRole = Qt.UserRole + 12
    TimestampRole = Qt.UserRole + 13
    TokensFreedRole = Qt.UserRole + 14
    CommandsRole = Qt.UserRole + 15
    FileRefsRole = Qt.UserRole + 16
    ContextStatsRole = Qt.UserRole + 17
    ProcessesRole = Qt.UserRole + 18
    PhaseNumberRole = Qt.UserRole + 19

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chunks: list[Chunk] = []

    def roleNames(self):
        return {
            self.ChunkIdRole: b"chunkId",
            self.ChunkTypeRole: b"chunkType",
            self.UserTextRole: b"userText",
            self.AiTextRole: b"aiText",
            self.SystemTextRole: b"systemText",
            self.StatusRole: b"status",
            self.ToolCountRole: b"toolCount",
            self.ToolExecutionsRole: b"toolExecutions",
            self.TokenCountRole: b"tokenCount",
            self.DurationRole: b"duration",
            self.CostRole: b"cost",
            self.ModelNameRole: b"modelName",
            self.TimestampRole: b"timestamp",
            self.TokensFreedRole: b"tokensFreed",
            self.CommandsRole: b"commands",
            self.FileRefsRole: b"fileRefs",
            self.ContextStatsRole: b"contextStats",
            self.ProcessesRole: b"processes",
            self.PhaseNumberRole: b"phaseNumber",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._chunks)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._chunks):
            return None

        chunk = self._chunks[index.row()]

        if role == self.ChunkIdRole:
            return chunk.id
        elif role == self.ChunkTypeRole:
            return chunk.chunk_type.value
        elif role == self.UserTextRole:
            if chunk.chunk_type == ChunkType.USER:
                return chunk.user_text or self._extract_user_text(chunk)
            return ""
        elif role == self.AiTextRole:
            if chunk.chunk_type == ChunkType.AI:
                return self._extract_ai_text(chunk)
            return ""
        elif role == self.SystemTextRole:
            if chunk.chunk_type == ChunkType.SYSTEM:
                return self._extract_system_text(chunk)
            return ""
        elif role == self.StatusRole:
            return chunk.status.value if hasattr(chunk, 'status') else ""
        elif role == self.ToolCountRole:
            return len(chunk.tool_executions)
        elif role == self.ToolExecutionsRole:
            return self._format_tool_executions(chunk.tool_executions)
        elif role == self.TokenCountRole:
            return chunk.metrics.total_tokens if chunk.metrics else 0
        elif role == self.DurationRole:
            return chunk.metrics.duration_ms if chunk.metrics else 0
        elif role == self.CostRole:
            return chunk.metrics.cost_usd if chunk.metrics else 0.0
        elif role == self.ModelNameRole:
            # Get model from the first assistant message in the chunk
            for msg in chunk.messages:
                if msg.model:
                    return msg.model
            return ""
        elif role == self.TimestampRole:
            return chunk.start_time.isoformat() if chunk.start_time else ""
        elif role == self.TokensFreedRole:
            return chunk.tokens_freed
        elif role == self.CommandsRole:
            return chunk.commands
        elif role == self.FileRefsRole:
            return chunk.file_references
        elif role == self.ContextStatsRole:
            return self._format_context_stats(chunk.context_stats)
        elif role == self.ProcessesRole:
            return self._format_processes(chunk.processes)
        elif role == self.PhaseNumberRole:
            return chunk.context_stats.phase_number if chunk.context_stats else 0
        return None

    def set_chunks(self, chunks: list[Chunk]):
        """Replace the entire chunk list."""
        self.beginResetModel()
        self._chunks = list(chunks)
        self.endResetModel()

    def _extract_user_text(self, chunk: Chunk) -> str:
        """Extract clean user text from chunk messages."""
        texts = []
        for msg in chunk.messages:
            if msg.role == "human" and msg.content:
                texts.append(extract_user_text(msg.content))
        return "\n".join(texts)

    def _extract_ai_text(self, chunk: Chunk) -> str:
        """Extract and sanitize AI text from chunk messages."""
        texts = []
        for msg in chunk.messages:
            if msg.role == "assistant" and msg.content:
                if isinstance(msg.content, str):
                    texts.append(sanitize_content(msg.content))
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(sanitize_content(block.get("text", "")))
        return "\n\n".join(t for t in texts if t)

    def _extract_system_text(self, chunk: Chunk) -> str:
        """Extract system text from chunk messages."""
        texts = []
        for msg in chunk.messages:
            if msg.content:
                if isinstance(msg.content, str):
                    texts.append(msg.content)
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))
        return "\n".join(t for t in texts if t)

    @staticmethod
    def _format_context_stats(stats) -> dict:
        """Convert ContextStats to a plain dict for QML."""
        if stats is None:
            return {}
        return {
            "totalEstimatedTokens": stats.total_estimated_tokens,
            "tokensByCategory": dict(stats.tokens_by_category),
            "phaseNumber": stats.phase_number,
            "newInjections": [
                {
                    "id": inj.id,
                    "category": inj.category.value,
                    "estimatedTokens": inj.estimated_tokens,
                    "path": inj.path,
                    "displayName": inj.display_name,
                }
                for inj in stats.new_injections
            ],
            "accumulatedInjections": [
                {
                    "id": inj.id,
                    "category": inj.category.value,
                    "estimatedTokens": inj.estimated_tokens,
                    "path": inj.path,
                    "displayName": inj.display_name,
                }
                for inj in stats.accumulated_injections
            ],
        }

    @staticmethod
    def _format_processes(processes) -> list[dict]:
        """Convert Process objects to plain dicts for QML."""
        if not processes:
            return []
        from claude_session_viewer.utils.token_estimator import estimate_tokens_for_content
        result = []
        for proc in processes:
            # Build simplified message list for display
            messages = []
            for msg in proc.messages:
                text = ""
                if isinstance(msg.content, str):
                    text = msg.content[:500]
                elif isinstance(msg.content, list):
                    parts = []
                    for block in msg.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    text = "\n".join(parts)[:500]
                tool_count = len(msg.tool_calls)
                messages.append({
                    "role": msg.role,
                    "text": text,
                    "toolCount": tool_count,
                })
            result.append({
                "id": proc.id,
                "description": proc.description,
                "subagentType": proc.subagent_type,
                "durationMs": proc.duration_ms,
                "tokenCount": proc.metrics.total_tokens if proc.metrics else 0,
                "costUsd": proc.metrics.cost_usd if proc.metrics else 0.0,
                "isParallel": proc.is_parallel,
                "memberName": proc.member_name,
                "memberColor": proc.member_color,
                "teamName": proc.team_name,
                "messages": messages,
            })
        return result

    @staticmethod
    def _format_tool_executions(executions: list[ToolExecution]) -> list[dict]:
        """Convert ToolExecution dataclasses to plain dicts for QML."""
        result = []
        for ex in executions:
            inp = ex.call.input if ex.call.input else {}
            raw_result = _get_result_text(ex.result) if ex.result else ""
            # Strip cat -n line numbers from Read/Glob results so QML gutter handles them
            result_text = strip_line_numbers(raw_result) if ex.call.name in ("Read", "Glob") else raw_result
            tool_dict = {
                "toolName": ex.call.name,
                "inputSummary": _summarize_input(ex.call),
                "resultSummary": _summarize_result(ex.result) if ex.result else "",
                "isError": ex.result.is_error if ex.result else False,
                "durationMs": ex.duration_ms,
                "inputData": _format_json(inp),
                "resultData": result_text,
                # Rich viewer fields
                "filePath": str(inp.get("file_path", "")),
                "fileExtension": get_file_extension(str(inp.get("file_path", ""))),
                "syntaxDefinition": get_syntax_definition(str(inp.get("file_path", ""))),
                "oldString": str(inp.get("old_string", "")),
                "newString": str(inp.get("new_string", "")),
                "replaceAll": bool(inp.get("replace_all", False)),
                "diffLines": _compute_diff_lines(inp),
                "command": str(inp.get("command", "")),
                "description": str(inp.get("description", "")),
                "pattern": str(inp.get("pattern", "")),
                "content": str(inp.get("content", "")),
                "lineOffset": int(inp.get("offset", 0)) if isinstance(inp.get("offset"), (int, float)) else 0,
                "lineLimit": int(inp.get("limit", 0)) if isinstance(inp.get("limit"), (int, float)) else 0,
            }
            result.append(tool_dict)
        return result


def _summarize_input(call) -> str:
    """Create a one-line summary of tool input."""
    inp = call.input
    if not inp:
        return ""
    if isinstance(inp, dict):
        # Common patterns
        if "command" in inp:
            return str(inp["command"])[:100]
        if "file_path" in inp:
            return str(inp["file_path"])
        if "query" in inp:
            return str(inp["query"])[:100]
        if "pattern" in inp:
            return str(inp["pattern"])[:100]
        # Fallback: first key=value
        for k, v in inp.items():
            return f"{k}: {str(v)[:80]}"
    return str(inp)[:100]


def _summarize_result(result) -> str:
    """Create a one-line summary of tool result."""
    if result is None:
        return ""
    content = result.content
    if isinstance(content, str):
        # First non-empty line, truncated
        for line in content.split("\n"):
            line = line.strip()
            if line:
                return line[:120]
        return ""
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                for line in text.split("\n"):
                    line = line.strip()
                    if line:
                        return line[:120]
        return ""
    return str(content)[:120]


def _format_json(data: dict) -> str:
    """Format a dict as readable JSON string."""
    import json
    try:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(data)


def _get_result_text(result) -> str:
    """Extract plain text from a tool result."""
    if result is None:
        return ""
    content = result.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return "\n".join(texts)
    return str(content)


def _compute_diff_lines(inp: dict) -> list[dict]:
    """Compute diff lines for Edit tool inputs."""
    old_str = inp.get("old_string", "")
    new_str = inp.get("new_string", "")
    if not old_str and not new_str:
        return []
    return compute_inline_diff(str(old_str), str(new_str))
