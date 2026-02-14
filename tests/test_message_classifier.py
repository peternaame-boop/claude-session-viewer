"""Tests for message classification."""

import pytest
from claude_session_viewer.utils.message_classifier import (
    classify_message,
    is_real_user_message,
    is_assistant_message,
)
from claude_session_viewer.types.messages import MessageType


class TestClassifyMessage:
    def test_real_user_message(self):
        raw = {"type": "user", "isMeta": False, "message": {"role": "user", "content": "hello"}}
        c = classify_message(raw)
        assert c.message_type == MessageType.USER
        assert c.is_meta is False
        assert c.is_noise is False
        assert c.role == "user"

    def test_meta_user_message(self):
        """isMeta:true + role:user = tool result fed back (system injection)."""
        raw = {"type": "user", "isMeta": True, "message": {"role": "user", "content": [{"type": "tool_result"}]}}
        c = classify_message(raw)
        assert c.is_meta is True
        assert c.is_system_injection is True

    def test_assistant_message(self):
        raw = {"type": "assistant", "isMeta": False, "message": {"role": "assistant", "content": "hi"}}
        c = classify_message(raw)
        assert c.message_type == MessageType.ASSISTANT
        assert c.role == "assistant"

    def test_compact_summary(self):
        raw = {"type": "summary", "isCompactSummary": True, "isMeta": True, "message": {"role": "assistant"}}
        c = classify_message(raw)
        assert c.is_compact is True
        assert c.is_noise is True  # summary type is hard noise

    def test_file_history_is_noise(self):
        raw = {"type": "file-history-snapshot", "isMeta": True, "message": {}}
        c = classify_message(raw)
        assert c.is_noise is True

    def test_queue_op_is_noise(self):
        raw = {"type": "queue-operation", "isMeta": True, "message": {}}
        c = classify_message(raw)
        assert c.is_noise is True

    def test_sidechain(self):
        raw = {"type": "assistant", "isSidechain": True, "isMeta": False, "message": {"role": "assistant"}}
        c = classify_message(raw)
        assert c.is_sidechain is True

    def test_unknown_type_defaults_system(self):
        raw = {"type": "unknown-type", "isMeta": False, "message": {}}
        c = classify_message(raw)
        assert c.message_type == MessageType.SYSTEM


class TestIsRealUserMessage:
    def test_real_user(self):
        assert is_real_user_message({"type": "user", "isMeta": False}) is True

    def test_meta_user(self):
        assert is_real_user_message({"type": "user", "isMeta": True}) is False

    def test_assistant(self):
        assert is_real_user_message({"type": "assistant", "isMeta": False}) is False

    def test_compact(self):
        assert is_real_user_message({"type": "user", "isMeta": False, "isCompactSummary": True}) is False


class TestIsAssistantMessage:
    def test_assistant(self):
        assert is_assistant_message({"type": "assistant", "message": {"role": "assistant"}}) is True

    def test_user(self):
        assert is_assistant_message({"type": "user", "message": {"role": "user"}}) is False

    def test_missing_message(self):
        assert is_assistant_message({"type": "assistant"}) is False
