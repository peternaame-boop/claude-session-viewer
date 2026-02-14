"""Tests for claude_session_viewer.services.metadata_cache."""

import os
import tempfile

import pytest

from claude_session_viewer.services.metadata_cache import MetadataCache
from claude_session_viewer.types import Session


@pytest.fixture
def cache(tmp_path):
    db_path = str(tmp_path / "test_cache.db")
    c = MetadataCache(db_path=db_path)
    yield c
    c.close()


def _make_session(
    session_id="sess-1",
    project_id="proj-1",
    file_path="/tmp/fake.jsonl",
    file_size=1024,
    first_message="Hello",
    message_count=5,
    is_ongoing=False,
    git_branch="main",
    created_at=1000000.0,
    modified_at=2000000.0,
) -> Session:
    return Session(
        id=session_id,
        project_id=project_id,
        project_path="/home/wiz/proj",
        file_path=file_path,
        file_size=file_size,
        created_at=created_at,
        modified_at=modified_at,
        first_message=first_message,
        message_count=message_count,
        is_ongoing=is_ongoing,
        git_branch=git_branch,
    )


class TestMetadataCacheGet:
    def test_get_nonexistent(self, cache):
        assert cache.get("nonexistent") is None

    def test_put_and_get(self, cache, tmp_path):
        # Create a real file so mtime lookup works
        f = tmp_path / "session.jsonl"
        f.write_text("{}")
        session = _make_session(file_path=str(f))
        cache.put(session)
        result = cache.get("sess-1")
        assert result is not None
        assert result.id == "sess-1"
        assert result.project_id == "proj-1"
        assert result.first_message == "Hello"
        assert result.message_count == 5
        assert result.git_branch == "main"

    def test_put_replaces_existing(self, cache, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text("{}")
        session1 = _make_session(file_path=str(f), first_message="v1")
        cache.put(session1)
        session2 = _make_session(file_path=str(f), first_message="v2")
        cache.put(session2)
        result = cache.get("sess-1")
        assert result.first_message == "v2"


class TestMetadataCacheProjectFilter:
    def test_get_for_project(self, cache, tmp_path):
        f1 = tmp_path / "s1.jsonl"
        f1.write_text("{}")
        f2 = tmp_path / "s2.jsonl"
        f2.write_text("{}")
        f3 = tmp_path / "s3.jsonl"
        f3.write_text("{}")

        cache.put(_make_session(session_id="s1", project_id="proj-a", file_path=str(f1), modified_at=3.0))
        cache.put(_make_session(session_id="s2", project_id="proj-a", file_path=str(f2), modified_at=1.0))
        cache.put(_make_session(session_id="s3", project_id="proj-b", file_path=str(f3), modified_at=2.0))

        results = cache.get_for_project("proj-a")
        assert len(results) == 2
        # Ordered by modified_at DESC
        assert results[0].id == "s1"
        assert results[1].id == "s2"

    def test_get_for_project_empty(self, cache):
        assert cache.get_for_project("nonexistent") == []


class TestMetadataCacheStaleness:
    def test_is_stale_not_cached(self, cache):
        assert cache.is_stale("unknown", 100, 1.0) is True

    def test_is_stale_matching(self, cache, tmp_path):
        f = tmp_path / "s.jsonl"
        f.write_text("{}")
        mtime = os.path.getmtime(str(f))
        size = os.path.getsize(str(f))
        session = _make_session(file_path=str(f), file_size=size)
        cache.put(session)
        assert cache.is_stale("sess-1", size, mtime) is False

    def test_is_stale_size_changed(self, cache, tmp_path):
        f = tmp_path / "s.jsonl"
        f.write_text("{}")
        session = _make_session(file_path=str(f), file_size=100)
        cache.put(session)
        mtime = os.path.getmtime(str(f))
        assert cache.is_stale("sess-1", 200, mtime) is True

    def test_is_stale_mtime_changed(self, cache, tmp_path):
        f = tmp_path / "s.jsonl"
        f.write_text("{}")
        session = _make_session(file_path=str(f), file_size=2)
        cache.put(session)
        assert cache.is_stale("sess-1", 2, 9999999.0) is True


class TestMetadataCacheRemoveAndClear:
    def test_remove(self, cache, tmp_path):
        f = tmp_path / "s.jsonl"
        f.write_text("{}")
        cache.put(_make_session(file_path=str(f)))
        cache.remove("sess-1")
        assert cache.get("sess-1") is None

    def test_clear(self, cache, tmp_path):
        f1 = tmp_path / "s1.jsonl"
        f1.write_text("{}")
        f2 = tmp_path / "s2.jsonl"
        f2.write_text("{}")
        cache.put(_make_session(session_id="s1", file_path=str(f1)))
        cache.put(_make_session(session_id="s2", file_path=str(f2)))
        cache.clear()
        assert cache.get("s1") is None
        assert cache.get("s2") is None
