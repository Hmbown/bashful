"""Git worktree management for isolated parallel agent work."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

WORKTREES_FILE = Path.home() / ".bashful" / "worktrees.json"


@dataclass
class WorktreeInfo:
    name: str
    path: str
    branch: str
    base_ref: str
    created_at: float
    repo: str | None = None
    job_id: str | None = None


def _git(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=30,
    )


def _repo_root(cwd: str | None = None) -> str:
    """Get the git repository root directory."""
    proc = _git("rev-parse", "--show-toplevel", cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(
            "Not inside a git repository. "
            "Worktree commands require a git repo."
        )
    return proc.stdout.strip()


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use as a branch/directory name."""
    return re.sub(r"[^a-zA-Z0-9._-]", "-", name).strip("-")


def _load_worktrees() -> list[WorktreeInfo]:
    if not WORKTREES_FILE.exists():
        return []
    try:
        raw = json.loads(WORKTREES_FILE.read_text())
        return [WorktreeInfo(**w) for w in raw]
    except (json.JSONDecodeError, TypeError):
        return []


def _save_worktrees(worktrees: list[WorktreeInfo]) -> None:
    WORKTREES_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(w) for w in worktrees]
    WORKTREES_FILE.write_text(json.dumps(data, indent=2))


def create_worktree(
    name: str,
    *,
    base_ref: str = "HEAD",
    repo_dir: str | None = None,
    job_id: str | None = None,
) -> WorktreeInfo:
    """Create a new git worktree for isolated work.

    Args:
        name: Human-friendly name (e.g. "claude-fix-auth").
        base_ref: Git ref to base the new branch on (default HEAD).
        repo_dir: Root of the git repo (auto-detected if None).
        job_id: Associate with a supervisor job.

    Returns:
        WorktreeInfo with the created worktree details.
    """
    safe_name = _sanitize_name(name)
    if not safe_name:
        raise ValueError(f"Invalid worktree name: {name!r}")

    root = _repo_root(repo_dir)
    root_path = Path(root)

    branch = f"bashful/{safe_name}"
    wt_path = root_path.parent / ".bashful-worktrees" / safe_name

    if wt_path.exists():
        raise ValueError(f"Worktree path already exists: {wt_path}")

    # Ensure parent exists
    wt_path.parent.mkdir(parents=True, exist_ok=True)

    proc = _git(
        "worktree", "add", "-b", branch, str(wt_path), base_ref,
        cwd=root,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {proc.stderr.strip()}")

    wt = WorktreeInfo(
        name=safe_name,
        path=str(wt_path),
        branch=branch,
        base_ref=base_ref,
        created_at=time.time(),
        repo=root,
        job_id=job_id,
    )

    # Persist to index
    worktrees = _load_worktrees()
    worktrees.append(wt)
    _save_worktrees(worktrees)

    return wt


def list_worktrees(*, repo_dir: str | None = None) -> list[WorktreeInfo]:
    """List bashful-managed worktrees for the current repo.

    Only returns worktrees whose ``repo`` matches the current (or given)
    repository root.  Worktrees created before the ``repo`` field existed
    (``repo is None``) are included as a migration courtesy.
    """
    try:
        root = _repo_root(repo_dir)
    except RuntimeError:
        root = None

    all_wts = _load_worktrees()

    # Validate: exists on disk AND belongs to this repo
    valid_all: list[WorktreeInfo] = []
    result: list[WorktreeInfo] = []
    for wt in all_wts:
        if not Path(wt.path).exists():
            continue
        valid_all.append(wt)
        if root is not None and (wt.repo is None or wt.repo == root):
            result.append(wt)

    # Prune disk-missing entries globally
    if len(valid_all) != len(all_wts):
        _save_worktrees(valid_all)

    return result


def get_worktree(name: str, *, repo_dir: str | None = None) -> WorktreeInfo | None:
    """Look up a worktree by name within the current repo."""
    for wt in list_worktrees(repo_dir=repo_dir):
        if wt.name == name:
            return wt
    return None


def remove_worktree(
    name: str,
    *,
    force: bool = False,
    repo_dir: str | None = None,
) -> bool:
    """Remove a worktree and optionally delete the branch.

    Returns True if the worktree was removed.
    """
    wt = get_worktree(name, repo_dir=repo_dir)
    if wt is None:
        return False

    root = _repo_root(repo_dir)

    # Remove the git worktree
    args = ["worktree", "remove", wt.path]
    if force:
        args.append("--force")
    proc = _git(*args, cwd=root)
    if proc.returncode != 0:
        if not force:
            raise RuntimeError(
                f"Failed to remove worktree: {proc.stderr.strip()}\n"
                "Use force=True to force removal."
            )
        return False

    # Try to delete the branch (non-fatal if it fails)
    _git("branch", "-d", wt.branch, cwd=root)

    # Remove from index
    worktrees = _load_worktrees()
    worktrees = [w for w in worktrees if w.name != name]
    _save_worktrees(worktrees)

    return True
