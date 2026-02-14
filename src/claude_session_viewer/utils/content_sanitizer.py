"""Sanitize message content for display, stripping internal markup."""

import re

# Patterns to strip from display content
_SYSTEM_REMINDER_RE = re.compile(
    r'<system-reminder>.*?</system-reminder>',
    re.DOTALL,
)
_TEAMMATE_MESSAGE_RE = re.compile(
    r'<teammate-message\b[^>]*>.*?</teammate-message>',
    re.DOTALL,
)
_LOCAL_COMMAND_RE = re.compile(
    r'<local-command-caveat>.*?</local-command-caveat>',
    re.DOTALL,
)
_COMMAND_NAME_RE = re.compile(
    r'<command-name>.*?</command-name>',
    re.DOTALL,
)
_COMMAND_MESSAGE_RE = re.compile(
    r'<command-message>.*?</command-message>',
    re.DOTALL,
)
_COMMAND_ARGS_RE = re.compile(
    r'<command-args>.*?</command-args>',
    re.DOTALL,
)
_LOCAL_STDOUT_RE = re.compile(
    r'<local-command-stdout>.*?</local-command-stdout>',
    re.DOTALL,
)

_ALL_PATTERNS = [
    _SYSTEM_REMINDER_RE,
    _TEAMMATE_MESSAGE_RE,
    _LOCAL_COMMAND_RE,
    _COMMAND_NAME_RE,
    _COMMAND_MESSAGE_RE,
    _COMMAND_ARGS_RE,
    _LOCAL_STDOUT_RE,
]


def sanitize_content(text: str) -> str:
    """Remove internal markup tags from content for clean display."""
    if not text:
        return ""
    result = text
    for pattern in _ALL_PATTERNS:
        result = pattern.sub("", result)
    # Clean up excessive whitespace left by removals
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def extract_user_text(content) -> str:
    """Extract the actual user-typed text from message content.

    Handles both string content and list-of-blocks content.
    Returns cleaned text suitable for display in user bubbles.
    """
    if isinstance(content, str):
        return sanitize_content(content)
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return sanitize_content("\n".join(texts))
    return ""


def extract_thinking_text(content) -> str:
    """Extract thinking block text from assistant content."""
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "thinking":
            parts.append(block.get("thinking", ""))
    return "\n\n".join(parts)


def extract_slash_commands(text: str) -> list[str]:
    """Extract slash commands from user text (e.g., /compact, /review)."""
    return re.findall(r'(?:^|\s)(\/[a-zA-Z][\w-]*)', text)


def extract_file_references(text: str) -> list[str]:
    """Extract @-mentioned file paths from user text."""
    return re.findall(r'@((?:/|\.\.?/)[^\s,;]+|[a-zA-Z][\w./\\-]+\.\w+)', text)
