"""Git metadata resolver — reads .git for branch and remote info."""

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_git_branch(project_path: str) -> str:
    """Read the current git branch from a project path.

    Handles both regular repos and worktrees (.git as file with gitdir pointer).
    """
    git_path = Path(project_path) / ".git"
    if not git_path.exists():
        return ""

    try:
        if git_path.is_file():
            # Worktree: .git is a file containing "gitdir: <path>"
            content = git_path.read_text().strip()
            if content.startswith("gitdir:"):
                gitdir = content[len("gitdir:"):].strip()
                head_path = Path(gitdir) / "HEAD"
            else:
                return ""
        else:
            head_path = git_path / "HEAD"

        if not head_path.exists():
            return ""

        head = head_path.read_text().strip()
        if head.startswith("ref: refs/heads/"):
            return head[len("ref: refs/heads/"):]
        # Detached HEAD — return short hash
        return head[:8] if len(head) >= 8 else head

    except (OSError, ValueError):
        logger.debug("Failed to resolve git branch for %s", project_path, exc_info=True)
        return ""


def resolve_remote_url(project_path: str) -> str:
    """Read the origin remote URL from a project's git config."""
    git_path = Path(project_path) / ".git"
    if not git_path.exists():
        return ""

    try:
        if git_path.is_file():
            content = git_path.read_text().strip()
            if content.startswith("gitdir:"):
                gitdir = Path(content[len("gitdir:"):].strip())
                # For worktrees, the main repo config is at the parent
                config_path = gitdir.parent.parent / "config"
                if not config_path.exists():
                    config_path = gitdir / "config"
            else:
                return ""
        else:
            config_path = git_path / "config"

        if not config_path.exists():
            return ""

        return _parse_remote_url(config_path)

    except (OSError, ValueError):
        logger.debug("Failed to resolve remote for %s", project_path, exc_info=True)
        return ""


def generate_repo_id(project_path: str) -> str:
    """Generate a stable repository ID from the normalized path.

    Uses the remote URL if available, otherwise the path itself.
    """
    remote = resolve_remote_url(project_path)
    key = remote if remote else str(Path(project_path).resolve())
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def is_worktree(project_path: str) -> bool:
    """Check if a project path is a git worktree."""
    git_path = Path(project_path) / ".git"
    return git_path.is_file()


def _parse_remote_url(config_path: Path) -> str:
    """Parse the origin remote URL from a git config file."""
    try:
        content = config_path.read_text()
    except OSError:
        return ""

    in_origin = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == '[remote "origin"]':
            in_origin = True
            continue
        if in_origin:
            if stripped.startswith("["):
                break  # Next section
            if stripped.startswith("url = "):
                return stripped[len("url = "):]
    return ""
