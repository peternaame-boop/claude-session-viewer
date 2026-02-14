"""Path validation and security sandboxing."""

import os
import re
from pathlib import Path

# Sensitive file patterns blocked from display
SENSITIVE_PATTERNS = [
    re.compile(r'[/\\]\.ssh[/\\]'),
    re.compile(r'[/\\]\.aws[/\\]'),
    re.compile(r'[/\\]\.config[/\\]gcloud[/\\]'),
    re.compile(r'[/\\]\.azure[/\\]'),
    re.compile(r'[/\\]\.env($|\.)'),
    re.compile(r'[/\\]\.git-credentials$'),
    re.compile(r'[/\\]\.gitconfig$'),
    re.compile(r'[/\\]\.npmrc$'),
    re.compile(r'[/\\]\.docker[/\\]config\.json$'),
    re.compile(r'[/\\]\.kube[/\\]config$'),
    re.compile(r'[/\\]id_rsa$'),
    re.compile(r'[/\\]id_ed25519$'),
    re.compile(r'[/\\]id_ecdsa$'),
    re.compile(r'\.pem$'),
    re.compile(r'\.key$'),
    re.compile(r'[/\\]etc[/\\]passwd$'),
    re.compile(r'[/\\]etc[/\\]shadow$'),
    re.compile(r'credentials\.json$'),
    re.compile(r'secrets\.json$'),
    re.compile(r'tokens\.json$'),
]


def is_sensitive_path(path: str) -> bool:
    """Check if a file path matches any sensitive pattern."""
    normalized = path.replace("\\", "/")
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def get_allowed_roots() -> list[str]:
    """Return the list of allowed root directories for file access."""
    home = os.path.expanduser("~")
    return [
        os.path.join(home, ".claude"),
    ]


def is_path_allowed(path: str, extra_roots: list[str] | None = None) -> bool:
    """Validate that a path is within allowed directories.

    Resolves symlinks before checking to prevent escape attacks.
    """
    try:
        resolved = os.path.realpath(os.path.expanduser(path))
    except (OSError, ValueError):
        return False

    allowed = get_allowed_roots()
    if extra_roots:
        allowed.extend(extra_roots)

    for root in allowed:
        try:
            resolved_root = os.path.realpath(os.path.expanduser(root))
            if resolved.startswith(resolved_root + os.sep) or resolved == resolved_root:
                return True
        except (OSError, ValueError):
            continue

    return False


def validate_session_path(path: str) -> bool:
    """Validate that a path points to a valid session file within ~/.claude/projects/."""
    if not path.endswith(".jsonl"):
        return False
    return is_path_allowed(path)


def sanitize_display_path(path: str) -> str:
    """Sanitize a path for safe display, masking sensitive portions."""
    if is_sensitive_path(path):
        return "[sensitive path hidden]"
    return path
