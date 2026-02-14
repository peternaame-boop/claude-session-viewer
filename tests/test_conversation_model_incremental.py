"""Tests for ConversationModel.update_chunks() incremental update."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from PySide6.QtCore import QModelIndex

from claude_session_viewer.models.conversation_model import ConversationModel
from claude_session_viewer.types import Chunk, ChunkType, SessionMetrics


def _make_chunk(chunk_id: str, chunk_type=ChunkType.USER, user_text="msg") -> Chunk:
    now = datetime.now(timezone.utc)
    return Chunk(
        id=chunk_id,
        chunk_type=chunk_type,
        start_time=now,
        end_time=now,
        metrics=SessionMetrics(),
        messages=[],
        user_text=user_text,
    )


class TestUpdateChunks:
    def test_appends_new_chunks_via_insert_rows(self, qapp):
        """New chunks at the end are inserted via beginInsertRows."""
        model = ConversationModel()
        initial = [_make_chunk("chunk-1"), _make_chunk("chunk-2", ChunkType.AI)]
        model.set_chunks(initial)
        assert model.rowCount() == 2

        # Spy on insert signals
        inserted = []
        model.rowsInserted.connect(lambda parent, first, last: inserted.append((first, last)))

        updated = [
            _make_chunk("chunk-1"),
            _make_chunk("chunk-2", ChunkType.AI),
            _make_chunk("chunk-3"),
            _make_chunk("chunk-4", ChunkType.AI),
        ]
        model.update_chunks(updated)

        assert model.rowCount() == 4
        assert len(inserted) == 1
        assert inserted[0] == (2, 3)  # rows 2-3 inserted

    def test_emits_data_changed_for_modified_last_chunk(self, qapp):
        """The last common chunk emits dataChanged (may have new content)."""
        model = ConversationModel()
        initial = [_make_chunk("chunk-1"), _make_chunk("chunk-2", ChunkType.AI)]
        model.set_chunks(initial)

        changed = []
        model.dataChanged.connect(lambda tl, br, roles: changed.append(tl.row()))

        # Same IDs but chunk-2 may have different content
        updated = [
            _make_chunk("chunk-1"),
            _make_chunk("chunk-2", ChunkType.AI, user_text="updated"),
        ]
        model.update_chunks(updated)

        # Should have emitted dataChanged for row 1 (chunk-2)
        assert 1 in changed

    def test_falls_back_to_full_reset_on_structural_change(self, qapp):
        """Completely different chunk IDs trigger a full model reset."""
        model = ConversationModel()
        initial = [_make_chunk("chunk-1"), _make_chunk("chunk-2")]
        model.set_chunks(initial)

        reset_count = []
        model.modelReset.connect(lambda: reset_count.append(1))

        # Completely different structure
        updated = [_make_chunk("chunk-X"), _make_chunk("chunk-Y")]
        model.update_chunks(updated)

        assert len(reset_count) == 1
        assert model.rowCount() == 2

    def test_handles_empty_to_non_empty_transition(self, qapp):
        """Going from empty model to having chunks works via full set."""
        model = ConversationModel()
        assert model.rowCount() == 0

        reset_count = []
        model.modelReset.connect(lambda: reset_count.append(1))

        model.update_chunks([_make_chunk("chunk-1")])

        assert model.rowCount() == 1
        assert len(reset_count) == 1  # Used set_chunks internally

    def test_handles_non_empty_to_empty_transition(self, qapp):
        """Going from chunks to empty works via full set."""
        model = ConversationModel()
        model.set_chunks([_make_chunk("chunk-1")])
        assert model.rowCount() == 1

        model.update_chunks([])
        assert model.rowCount() == 0

    def test_no_insert_when_only_last_chunk_changes(self, qapp):
        """If same number of chunks, only dataChanged fires, no insert."""
        model = ConversationModel()
        initial = [_make_chunk("chunk-1"), _make_chunk("chunk-2")]
        model.set_chunks(initial)

        inserted = []
        model.rowsInserted.connect(lambda p, f, l: inserted.append((f, l)))

        changed = []
        model.dataChanged.connect(lambda tl, br, roles: changed.append(tl.row()))

        updated = [_make_chunk("chunk-1"), _make_chunk("chunk-2", user_text="new")]
        model.update_chunks(updated)

        assert len(inserted) == 0
        assert 1 in changed  # last common chunk updated


class TestPagination:
    def test_set_chunks_paginates_large_list(self, qapp):
        """set_chunks only exposes last PAGE_SIZE chunks to QML."""
        from claude_session_viewer.models.conversation_model import _PAGE_SIZE

        model = ConversationModel()
        chunks = [_make_chunk(f"chunk-{i}") for i in range(500)]
        model.set_chunks(chunks)

        assert model.rowCount() == _PAGE_SIZE
        assert model._get_total_chunk_count() == 500
        assert model._get_can_load_earlier()

    def test_set_chunks_small_list_no_pagination(self, qapp):
        """Small list doesn't paginate."""
        model = ConversationModel()
        chunks = [_make_chunk(f"chunk-{i}") for i in range(10)]
        model.set_chunks(chunks)

        assert model.rowCount() == 10
        assert model._get_total_chunk_count() == 10
        assert not model._get_can_load_earlier()

    def test_load_earlier_prepends_chunks(self, qapp):
        """load_earlier() prepends an earlier page of chunks."""
        from claude_session_viewer.models.conversation_model import _PAGE_SIZE

        model = ConversationModel()
        chunks = [_make_chunk(f"chunk-{i}") for i in range(500)]
        model.set_chunks(chunks)

        initial_count = model.rowCount()
        assert initial_count == _PAGE_SIZE

        model.load_earlier()

        # offset was 300, new_start = max(0, 300-200) = 100, prepend 200 more
        # visible = 200 (original) + 200 (prepended) = 400
        assert model.rowCount() == 400
        assert model._get_can_load_earlier()  # still 100 chunks earlier

    def test_load_earlier_stops_at_zero(self, qapp):
        """load_earlier() stops when all chunks are visible."""
        from claude_session_viewer.models.conversation_model import _PAGE_SIZE

        model = ConversationModel()
        chunks = [_make_chunk(f"chunk-{i}") for i in range(250)]
        model.set_chunks(chunks)

        # offset = 50, visible = 200
        model.load_earlier()

        # offset should now be 0, all 250 visible
        assert model.rowCount() == 250
        assert not model._get_can_load_earlier()

        # Calling again should be a no-op
        model.load_earlier()
        assert model.rowCount() == 250
