"""Regex pattern validation and safe matching utilities."""

import re
import signal
from typing import Match


# Safety limits
MAX_PATTERN_LENGTH = 100
_NESTED_QUANTIFIER_RE = re.compile(r"[+*?]\??[+*?]|(?:\{[^}]+\})[+*?]")


def validate_regex(pattern: str) -> tuple[bool, str]:
    """Validate a regex pattern for safety and correctness.

    Returns (is_valid, error_message). If valid, error_message is empty.

    Checks:
    - Non-empty
    - Length <= MAX_PATTERN_LENGTH
    - Balanced brackets and parentheses
    - No nested quantifiers (catastrophic backtracking risk)
    - Compilable by re module
    """
    if not pattern:
        return False, "Pattern is empty"

    if len(pattern) > MAX_PATTERN_LENGTH:
        return False, f"Pattern exceeds {MAX_PATTERN_LENGTH} characters"

    # Check bracket balance
    if not _brackets_balanced(pattern):
        return False, "Unbalanced brackets or parentheses"

    # Check for nested quantifiers (e.g. a++, a*+, a{2}*)
    if _NESTED_QUANTIFIER_RE.search(pattern):
        return False, "Nested quantifiers detected (backtracking risk)"

    # Try compiling
    try:
        re.compile(pattern)
    except re.error as e:
        return False, f"Invalid regex: {e}"

    return True, ""


def safe_match(
    pattern: str, text: str, timeout_ms: int = 1000
) -> Match | None:
    """Execute a regex search with a timeout to prevent catastrophic backtracking.

    Uses signal.alarm on POSIX systems. Returns None on timeout or error.
    """

    class _Timeout(Exception):
        pass

    def _handler(signum, frame):
        raise _Timeout

    timeout_sec = max(1, timeout_ms // 1000)
    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(timeout_sec)
        result = re.search(pattern, text)
        signal.alarm(0)
        return result
    except (_Timeout, re.error):
        return None
    finally:
        signal.alarm(0)
        if old_handler is not None:
            signal.signal(signal.SIGALRM, old_handler)


def _brackets_balanced(pattern: str) -> bool:
    """Check that () [] are balanced, respecting escapes."""
    stack = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            i += 2  # skip escaped char
            continue
        if ch in ("(", "["):
            stack.append(ch)
        elif ch == ")":
            if not stack or stack[-1] != "(":
                return False
            stack.pop()
        elif ch == "]":
            if not stack or stack[-1] != "[":
                return False
            stack.pop()
        i += 1
    return len(stack) == 0
