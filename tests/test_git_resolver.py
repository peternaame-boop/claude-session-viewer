"""Tests for claude_session_viewer.services.git_resolver."""

from pathlib import Path

import pytest

from claude_session_viewer.services.git_resolver import (
    resolve_git_branch,
    resolve_remote_url,
    generate_repo_id,
    is_worktree,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a fake git repo with HEAD on main branch."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (git_dir / "config").write_text(
        '[core]\n\trepositoryformatversion = 0\n'
        '[remote "origin"]\n\turl = git@github.com:user/repo.git\n'
        '\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
    )
    return tmp_path


@pytest.fixture
def worktree_repo(tmp_path, git_repo):
    """Create a fake worktree pointing at git_repo."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    # .git is a file, not a directory
    (wt / ".git").write_text(f"gitdir: {git_repo / '.git'}\n")
    return wt


# ---------------------------------------------------------------------------
# 1. Resolve branch from regular repo
# ---------------------------------------------------------------------------

def test_resolve_branch(git_repo):
    """resolve_git_branch reads the branch from .git/HEAD."""
    branch = resolve_git_branch(str(git_repo))
    assert branch == "main"


# ---------------------------------------------------------------------------
# 2. Resolve detached HEAD
# ---------------------------------------------------------------------------

def test_resolve_detached_head(git_repo):
    """Detached HEAD returns short hash."""
    (git_repo / ".git" / "HEAD").write_text("abc1234567890def\n")
    branch = resolve_git_branch(str(git_repo))
    assert branch == "abc12345"


# ---------------------------------------------------------------------------
# 3. No .git directory
# ---------------------------------------------------------------------------

def test_no_git_dir(tmp_path):
    """No .git returns empty string."""
    branch = resolve_git_branch(str(tmp_path))
    assert branch == ""


# ---------------------------------------------------------------------------
# 4. Resolve remote URL
# ---------------------------------------------------------------------------

def test_resolve_remote_url(git_repo):
    """resolve_remote_url extracts the origin URL from git config."""
    url = resolve_remote_url(str(git_repo))
    assert url == "git@github.com:user/repo.git"


# ---------------------------------------------------------------------------
# 5. No remote returns empty
# ---------------------------------------------------------------------------

def test_no_remote(tmp_path):
    """No .git config returns empty remote URL."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (git_dir / "config").write_text("[core]\n\tbare = false\n")

    url = resolve_remote_url(str(tmp_path))
    assert url == ""


# ---------------------------------------------------------------------------
# 6. Generate repo ID is stable
# ---------------------------------------------------------------------------

def test_repo_id_stable(git_repo):
    """Same repo path generates the same ID."""
    id1 = generate_repo_id(str(git_repo))
    id2 = generate_repo_id(str(git_repo))
    assert id1 == id2
    assert len(id1) == 12


# ---------------------------------------------------------------------------
# 7. Worktree detection
# ---------------------------------------------------------------------------

def test_is_worktree(worktree_repo, git_repo):
    """is_worktree correctly identifies worktrees vs regular repos."""
    assert is_worktree(str(worktree_repo)) is True
    assert is_worktree(str(git_repo)) is False


# ---------------------------------------------------------------------------
# 8. Worktree branch resolution
# ---------------------------------------------------------------------------

def test_worktree_branch(worktree_repo):
    """resolve_git_branch follows worktree gitdir pointer."""
    branch = resolve_git_branch(str(worktree_repo))
    assert branch == "main"
