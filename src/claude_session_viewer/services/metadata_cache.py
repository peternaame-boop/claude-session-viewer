"""SQLite metadata cache for session scanning results."""

import sqlite3
import os
from pathlib import Path
from claude_session_viewer.types import Session


class MetadataCache:
    """Caches session metadata to avoid re-parsing JSONL files."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            cache_dir = Path.home() / ".cache" / "claude-session-viewer"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(cache_dir / "sessions.db")
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS session_metadata (
                session_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                first_message TEXT NOT NULL DEFAULT '',
                message_count INTEGER NOT NULL DEFAULT 0,
                is_ongoing INTEGER NOT NULL DEFAULT 0,
                git_branch TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                modified_at REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_id
            ON session_metadata(project_id)
        """)
        self._conn.commit()

    def get(self, session_id: str) -> Session | None:
        row = self._conn.execute(
            "SELECT * FROM session_metadata WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def get_for_project(self, project_id: str) -> list[Session]:
        rows = self._conn.execute(
            "SELECT * FROM session_metadata WHERE project_id = ? ORDER BY modified_at DESC",
            (project_id,)
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def put(self, session: Session):
        self._conn.execute("""
            INSERT OR REPLACE INTO session_metadata
            (session_id, project_id, file_path, file_size, mtime,
             first_message, message_count, is_ongoing, git_branch,
             created_at, modified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id, session.project_id, session.file_path,
            session.file_size, os.path.getmtime(session.file_path) if os.path.exists(session.file_path) else session.modified_at,
            session.first_message, session.message_count,
            1 if session.is_ongoing else 0, session.git_branch,
            session.created_at, session.modified_at
        ))
        self._conn.commit()

    def is_stale(self, session_id: str, file_size: int, mtime: float) -> bool:
        row = self._conn.execute(
            "SELECT file_size, mtime FROM session_metadata WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        if row is None:
            return True
        return row["file_size"] != file_size or abs(row["mtime"] - mtime) > 0.001

    def remove(self, session_id: str):
        self._conn.execute(
            "DELETE FROM session_metadata WHERE session_id = ?",
            (session_id,)
        )
        self._conn.commit()

    def clear(self):
        self._conn.execute("DELETE FROM session_metadata")
        self._conn.commit()

    def close(self):
        self._conn.close()

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["session_id"],
            project_id=row["project_id"],
            project_path="",  # Not stored in cache, derived at runtime
            file_path=row["file_path"],
            file_size=row["file_size"],
            created_at=row["created_at"],
            modified_at=row["modified_at"],
            first_message=row["first_message"],
            message_count=row["message_count"],
            is_ongoing=bool(row["is_ongoing"]),
            git_branch=row["git_branch"],
        )
