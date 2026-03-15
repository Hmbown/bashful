"""Tests for worktree management."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from bashful.worktree import (
    WorktreeInfo,
    _sanitize_name,
    create_worktree,
    get_worktree,
    list_worktrees,
    remove_worktree,
    WORKTREES_FILE,
)


class TestSanitizeName:
    def test_clean_name(self):
        assert _sanitize_name("fix-auth") == "fix-auth"

    def test_spaces(self):
        assert _sanitize_name("fix auth bug") == "fix-auth-bug"

    def test_special_chars(self):
        assert _sanitize_name("fix/auth@bug!") == "fix-auth-bug"

    def test_leading_trailing_dashes(self):
        assert _sanitize_name("--name--") == "name"


class TestCreateWorktree:
    def test_creates_worktree(self, tmp_path):
        mock_git = MagicMock()
        mock_git.return_value = MagicMock(returncode=0, stdout="/repo\n", stderr="")

        wt_file = tmp_path / "worktrees.json"

        with (
            patch("bashful.worktree._git", mock_git),
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree.Path.exists", return_value=False),
            patch("bashful.worktree.Path.mkdir"),
        ):
            # First call is repo root, second is git worktree add
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout="/repo\n"),  # rev-parse
                MagicMock(returncode=0, stdout="", stderr=""),  # worktree add
            ]
            wt = create_worktree("fix-auth")

        assert wt.name == "fix-auth"
        assert wt.branch == "bashful/fix-auth"
        assert "fix-auth" in wt.path

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            create_worktree("///")

    def test_existing_path_raises(self, tmp_path):
        with (
            patch("bashful.worktree._repo_root", return_value=str(tmp_path / "repo")),
        ):
            # Create the worktree path so it already exists
            wt_path = tmp_path / ".bashful-worktrees" / "exists"
            wt_path.mkdir(parents=True)

            with pytest.raises(ValueError, match="already exists"):
                create_worktree("exists", repo_dir=str(tmp_path / "repo"))

    def test_git_failure_raises(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"

        with (
            patch("bashful.worktree._git") as mock_git,
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree.Path.exists", return_value=False),
            patch("bashful.worktree.Path.mkdir"),
        ):
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout="/repo\n"),  # rev-parse
                MagicMock(returncode=128, stdout="", stderr="fatal: error"),  # worktree add
            ]
            with pytest.raises(RuntimeError, match="worktree add failed"):
                create_worktree("bad")


class TestListWorktrees:
    def test_empty(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"
        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/repo"),
        ):
            assert list_worktrees() == []

    def test_prunes_stale(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"
        # One valid, one stale
        valid_path = tmp_path / "valid"
        valid_path.mkdir()
        data = [
            {"name": "valid", "path": str(valid_path), "branch": "b", "base_ref": "HEAD", "created_at": 0, "repo": "/repo"},
            {"name": "stale", "path": "/nonexistent/path", "branch": "b", "base_ref": "HEAD", "created_at": 0, "repo": "/repo"},
        ]
        wt_file.write_text(json.dumps(data))

        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/repo"),
        ):
            result = list_worktrees()

        assert len(result) == 1
        assert result[0].name == "valid"
        # Check it saved back
        saved = json.loads(wt_file.read_text())
        assert len(saved) == 1

    def test_filters_by_repo(self, tmp_path):
        """Worktrees from a different repo should not appear."""
        wt_file = tmp_path / "worktrees.json"
        path_a = tmp_path / "wt-a"
        path_b = tmp_path / "wt-b"
        path_a.mkdir()
        path_b.mkdir()
        data = [
            {"name": "wt-a", "path": str(path_a), "branch": "b", "base_ref": "HEAD", "created_at": 0, "repo": "/repo-a"},
            {"name": "wt-b", "path": str(path_b), "branch": "b", "base_ref": "HEAD", "created_at": 0, "repo": "/repo-b"},
        ]
        wt_file.write_text(json.dumps(data))

        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/repo-a"),
        ):
            result = list_worktrees()

        assert len(result) == 1
        assert result[0].name == "wt-a"

    def test_legacy_worktrees_without_repo_included(self, tmp_path):
        """Worktrees without a repo field (legacy) should still be listed."""
        wt_file = tmp_path / "worktrees.json"
        wt_path = tmp_path / "legacy"
        wt_path.mkdir()
        data = [
            {"name": "legacy", "path": str(wt_path), "branch": "b", "base_ref": "HEAD", "created_at": 0},
        ]
        wt_file.write_text(json.dumps(data))

        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/any-repo"),
        ):
            result = list_worktrees()

        assert len(result) == 1
        assert result[0].name == "legacy"


class TestGetWorktree:
    def test_found(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"
        wt_path = tmp_path / "wt"
        wt_path.mkdir()
        data = [
            {"name": "mine", "path": str(wt_path), "branch": "b", "base_ref": "HEAD", "created_at": 0, "repo": "/repo"},
        ]
        wt_file.write_text(json.dumps(data))

        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/repo"),
        ):
            wt = get_worktree("mine")
        assert wt is not None
        assert wt.name == "mine"

    def test_not_found(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"
        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/repo"),
        ):
            assert get_worktree("nope") is None


class TestRemoveWorktree:
    def test_remove(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"
        wt_path = tmp_path / "wt"
        wt_path.mkdir()
        data = [
            {"name": "rm-me", "path": str(wt_path), "branch": "bashful/rm-me", "base_ref": "HEAD", "created_at": 0, "repo": str(tmp_path)},
        ]
        wt_file.write_text(json.dumps(data))

        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value=str(tmp_path)),
            patch("bashful.worktree._git") as mock_git,
        ):
            mock_git.return_value = MagicMock(returncode=0, stdout="", stderr="")
            removed = remove_worktree("rm-me")

        assert removed
        # Verify git commands were called
        calls = mock_git.call_args_list
        assert any("worktree" in str(c) for c in calls)

    def test_remove_not_found(self, tmp_path):
        wt_file = tmp_path / "worktrees.json"
        with (
            patch("bashful.worktree.WORKTREES_FILE", wt_file),
            patch("bashful.worktree._repo_root", return_value="/repo"),
        ):
            assert remove_worktree("nope") is False
