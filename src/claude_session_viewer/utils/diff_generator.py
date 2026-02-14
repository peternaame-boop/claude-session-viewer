"""Diff computation and text processing for rich viewers."""

import difflib
import os
import re


def compute_unified_diff(old_string: str, new_string: str, file_path: str = "") -> str:
    """Compute a unified diff between old and new strings.

    Returns a string with unified diff format lines.
    """
    filename = os.path.basename(file_path) if file_path else "file"
    old_lines = old_string.splitlines(keepends=True)
    new_lines = new_string.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "\n".join(diff)


def compute_inline_diff(old_string: str, new_string: str) -> list[dict]:
    """Compute an inline diff returning a list of line dicts for QML rendering.

    Each dict has:
        - text: str (the line content)
        - type: str ("removed", "added", "context", "header")
    """
    old_lines = old_string.splitlines()
    new_lines = new_string.splitlines()

    result = []

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in old_lines[i1:i2]:
                result.append({"text": " " + line, "type": "context"})
        elif tag == "delete":
            for line in old_lines[i1:i2]:
                result.append({"text": "-" + line, "type": "removed"})
        elif tag == "insert":
            for line in new_lines[j1:j2]:
                result.append({"text": "+" + line, "type": "added"})
        elif tag == "replace":
            for line in old_lines[i1:i2]:
                result.append({"text": "-" + line, "type": "removed"})
            for line in new_lines[j1:j2]:
                result.append({"text": "+" + line, "type": "added"})

    return result


def get_file_extension(file_path: str) -> str:
    """Extract file extension without the dot."""
    if not file_path:
        return ""
    basename = os.path.basename(file_path)
    _, ext = os.path.splitext(basename)
    if not ext and basename.startswith(".") and len(basename) > 1:
        # Dotfiles like .gitignore have no ext per os.path.splitext;
        # treat the name after the dot as the extension.
        return basename[1:].lower()
    return ext.lstrip(".").lower() if ext else ""


# Map file extensions to KSyntaxHighlighting definition names
EXTENSION_TO_SYNTAX = {
    "py": "Python",
    "js": "JavaScript",
    "ts": "TypeScript",
    "tsx": "TypeScript React (TSX)",
    "jsx": "JavaScript React (JSX)",
    "json": "JSON",
    "yaml": "YAML",
    "yml": "YAML",
    "toml": "TOML",
    "md": "Markdown",
    "html": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "sh": "Bash",
    "bash": "Bash",
    "fish": "Fish",
    "zsh": "Zsh",
    "rs": "Rust",
    "go": "Go",
    "java": "Java",
    "kt": "Kotlin",
    "c": "C",
    "cpp": "C++",
    "h": "C",
    "hpp": "C++",
    "rb": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "lua": "Lua",
    "sql": "SQL",
    "xml": "XML",
    "qml": "QML",
    "cmake": "CMake",
    "makefile": "Makefile",
    "dockerfile": "Dockerfile",
    "ini": "INI Files",
    "conf": "Apache Configuration",
    "txt": "",
    "log": "",
}


_CAT_N_PATTERN = re.compile(r"^\s+\d+[\t\u2192]")


def strip_line_numbers(text: str) -> str:
    """Strip cat -n style line numbers from text.

    Handles formats like '     1\\tcode' and '     1→code'.
    Returns the code content without line number prefixes.
    """
    if not text:
        return ""
    lines = text.split("\n")
    # Check if the first non-empty line matches cat -n format
    for line in lines:
        if line.strip():
            if not _CAT_N_PATTERN.match(line):
                return text  # Not cat -n format, return unchanged
            break
    else:
        return text  # All empty lines

    stripped = []
    for line in lines:
        if not line.strip():
            stripped.append("")
        else:
            # Remove leading spaces + digits + tab/arrow separator
            cleaned = re.sub(r"^\s+\d+[\t\u2192]", "", line)
            stripped.append(cleaned)
    return "\n".join(stripped)


def get_syntax_definition(file_path: str) -> str:
    """Get KSyntaxHighlighting definition name for a file path."""
    ext = get_file_extension(file_path)
    if ext in EXTENSION_TO_SYNTAX:
        return EXTENSION_TO_SYNTAX[ext]

    # Check filename-based matches
    basename = os.path.basename(file_path).lower() if file_path else ""
    if basename == "makefile":
        return "Makefile"
    if basename == "dockerfile":
        return "Dockerfile"
    if basename.endswith(".env") or basename == ".env":
        return "Bash"

    return ""
