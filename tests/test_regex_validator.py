"""Tests for claude_session_viewer.utils.regex_validator."""

from claude_session_viewer.utils.regex_validator import (
    validate_regex,
    safe_match,
    MAX_PATTERN_LENGTH,
)


# ---------------------------------------------------------------------------
# 1. Valid simple pattern
# ---------------------------------------------------------------------------

def test_valid_simple_pattern():
    """A basic regex like 'hello' should pass validation."""
    ok, err = validate_regex("hello")
    assert ok is True
    assert err == ""


# ---------------------------------------------------------------------------
# 2. Valid complex pattern
# ---------------------------------------------------------------------------

def test_valid_complex_pattern():
    """A pattern with groups, alternation, and quantifiers should pass."""
    ok, err = validate_regex(r"(foo|bar)\d{1,3}")
    assert ok is True
    assert err == ""


# ---------------------------------------------------------------------------
# 3. Empty pattern rejected
# ---------------------------------------------------------------------------

def test_empty_pattern_rejected():
    """An empty pattern should be rejected."""
    ok, err = validate_regex("")
    assert ok is False
    assert "empty" in err.lower()


# ---------------------------------------------------------------------------
# 4. Pattern too long
# ---------------------------------------------------------------------------

def test_pattern_too_long():
    """A pattern exceeding MAX_PATTERN_LENGTH should be rejected."""
    long_pattern = "a" * (MAX_PATTERN_LENGTH + 1)
    ok, err = validate_regex(long_pattern)
    assert ok is False
    assert str(MAX_PATTERN_LENGTH) in err


# ---------------------------------------------------------------------------
# 5. Unbalanced parentheses
# ---------------------------------------------------------------------------

def test_unbalanced_parentheses():
    """Unmatched '(' should fail validation."""
    ok, err = validate_regex("(foo")
    assert ok is False
    assert "unbalanced" in err.lower()


# ---------------------------------------------------------------------------
# 6. Nested quantifiers detected
# ---------------------------------------------------------------------------

def test_nested_quantifiers():
    """Patterns with nested quantifiers like a++ should fail."""
    ok, err = validate_regex("a*+")
    assert ok is False
    assert "nested" in err.lower() or "backtracking" in err.lower()


# ---------------------------------------------------------------------------
# 7. Invalid regex syntax
# ---------------------------------------------------------------------------

def test_invalid_regex_syntax():
    """A pattern with invalid syntax (e.g. lone '*') should fail."""
    ok, err = validate_regex("*abc")
    assert ok is False
    assert "invalid" in err.lower() or "regex" in err.lower()


# ---------------------------------------------------------------------------
# 8. safe_match returns a match
# ---------------------------------------------------------------------------

def test_safe_match_finds_match():
    """safe_match should return a Match object for a valid pattern and text."""
    result = safe_match(r"\d+", "abc 123 def")
    assert result is not None
    assert result.group() == "123"


# ---------------------------------------------------------------------------
# 9. safe_match returns None for no match
# ---------------------------------------------------------------------------

def test_safe_match_no_match():
    """safe_match should return None when the pattern doesn't match."""
    result = safe_match(r"xyz", "abc 123 def")
    assert result is None


# ---------------------------------------------------------------------------
# 10. safe_match handles invalid pattern
# ---------------------------------------------------------------------------

def test_safe_match_invalid_pattern():
    """safe_match should return None for an invalid regex, not raise."""
    result = safe_match("[invalid", "some text")
    assert result is None


# ---------------------------------------------------------------------------
# 11. Escaped brackets are balanced
# ---------------------------------------------------------------------------

def test_escaped_brackets_balanced():
    r"""Escaped brackets like \( should not count as unbalanced."""
    ok, err = validate_regex(r"\(literal\)")
    assert ok is True
    assert err == ""
