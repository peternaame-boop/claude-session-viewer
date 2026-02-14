"""Classify JSONL messages for chunk building and display filtering."""

from claude_session_viewer.types.messages import MessageType


# Message types that are pure noise (never displayed)
HARD_NOISE_TYPES = frozenset({
    MessageType.SUMMARY,
    MessageType.FILE_HISTORY,
    MessageType.QUEUE_OP,
})


class MessageClassification:
    """Result of classifying a raw JSONL line."""
    __slots__ = (
        "message_type", "is_meta", "is_noise", "is_compact",
        "is_sidechain", "is_system_injection", "role",
    )

    def __init__(
        self,
        message_type: MessageType,
        is_meta: bool = False,
        is_noise: bool = False,
        is_compact: bool = False,
        is_sidechain: bool = False,
        is_system_injection: bool = False,
        role: str = "",
    ):
        self.message_type = message_type
        self.is_meta = is_meta
        self.is_noise = is_noise
        self.is_compact = is_compact
        self.is_sidechain = is_sidechain
        self.is_system_injection = is_system_injection
        self.role = role


def classify_message(raw: dict) -> MessageClassification:
    """Classify a raw JSONL dict into its display category.

    Key logic:
    - isMeta: false + role: user → real user message (starts UserChunk)
    - isMeta: true → internal message (part of AIChunk)
    - isCompactSummary: true → compaction boundary (CompactChunk)
    - type in HARD_NOISE → filtered out entirely
    - isSidechain: true → sidechain (secondary context)
    """
    msg_type_str = raw.get("type", "")
    try:
        msg_type = MessageType(msg_type_str)
    except ValueError:
        msg_type = MessageType.SYSTEM

    is_meta = raw.get("isMeta", False)
    is_compact = raw.get("isCompactSummary", False)
    is_sidechain = raw.get("isSidechain", False)

    message = raw.get("message", {})
    role = message.get("role", "") if isinstance(message, dict) else ""

    # Hard noise: never display
    is_noise = msg_type in HARD_NOISE_TYPES

    # System injections: isMeta true with role user (tool results fed back)
    is_system_injection = is_meta and role == "user"

    return MessageClassification(
        message_type=msg_type,
        is_meta=is_meta,
        is_noise=is_noise,
        is_compact=is_compact,
        is_sidechain=is_sidechain,
        is_system_injection=is_system_injection,
        role=role,
    )


def is_real_user_message(raw: dict) -> bool:
    """Quick check: is this a real human-typed message?"""
    return (
        not raw.get("isMeta", False)
        and not raw.get("isCompactSummary", False)
        and raw.get("type") == "user"
    )


def is_assistant_message(raw: dict) -> bool:
    """Quick check: is this an AI response message?"""
    message = raw.get("message", {})
    role = message.get("role", "") if isinstance(message, dict) else ""
    return raw.get("type") == "assistant" and role == "assistant"
