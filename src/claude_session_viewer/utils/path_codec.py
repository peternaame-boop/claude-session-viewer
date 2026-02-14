"""Encode and decode Claude Code project path ↔ directory name."""

import re


def encode_path(path: str) -> str:
    """Encode a filesystem path to a Claude project directory name.

    /home/wiz/AI/LLM → -home-wiz-AI-LLM
    """
    if not path:
        return ""
    # Replace all path separators with hyphens
    encoded = path.replace("/", "-")
    # On Windows-origin paths, also handle backslash
    encoded = encoded.replace("\\", "-")
    return encoded


def decode_path(encoded: str) -> str:
    """Decode a Claude project directory name to a filesystem path.

    -home-wiz-AI-LLM → /home/wiz/AI/LLM
    """
    if not encoded:
        return ""
    # Strip composite ID suffix (e.g., ::a1b2c3d4)
    encoded = strip_composite_suffix(encoded)
    # Replace leading hyphen with /
    # Then replace remaining hyphens with /
    decoded = encoded.replace("-", "/")
    return decoded


def strip_composite_suffix(project_id: str) -> str:
    """Remove the ::hex suffix from composite project IDs.

    -home-wiz-project::a1b2c3d4 → -home-wiz-project
    """
    match = re.match(r'^(.+?)::[0-9a-fA-F]{8}$', project_id)
    if match:
        return match.group(1)
    return project_id


def extract_project_name(project_id: str) -> str:
    """Get the last path segment as the project display name.

    -home-wiz-AI-LLM → LLM
    """
    path = decode_path(project_id)
    return path.rstrip("/").rsplit("/", 1)[-1] if path else ""
