"""Tests for artifact persistence."""

import json
import os
from unittest.mock import patch

import pytest

from bashful.artifacts import (
    ARTIFACTS_DIR,
    list_artifacts,
    save_dialectic_artifact,
    save_fanout_artifact,
    save_matrix_artifact,
    save_review_artifact,
    save_run_artifact,
    show_artifact,
)
from bashful.fanout import FanoutError
from bashful.runner import RunResult


@pytest.fixture(autouse=True)
def tmp_artifacts_dir(tmp_path, monkeypatch):
    """Redirect ARTIFACTS_DIR to a temp directory for every test."""
    test_dir = tmp_path / "artifacts"
    monkeypatch.setattr("bashful.artifacts.ARTIFACTS_DIR", test_dir)
    return test_dir


def _run_result(**overrides):
    defaults = dict(
        agent_id="claude",
        command=["claude", "-p", "hello"],
        stdout="Hello world",
        stderr="",
        exit_code=0,
        duration_s=1.23,
        timed_out=False,
        mode="read",
    )
    defaults.update(overrides)
    return RunResult(**defaults)


class TestSaveRunArtifact:
    def test_creates_file(self, tmp_artifacts_dir):
        result = _run_result()
        aid = save_run_artifact(result, "hello")
        assert aid.startswith("run-claude-")
        path = tmp_artifacts_dir / f"{aid}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["type"] == "run"
        assert data["agent"] == "claude"
        assert data["prompt"] == "hello"
        assert data["stdout"] == "Hello world"
        assert data["exit_code"] == 0

    def test_stores_mode(self, tmp_artifacts_dir):
        result = _run_result(mode="write")
        aid = save_run_artifact(result, "fix it")
        data = json.loads((tmp_artifacts_dir / f"{aid}.json").read_text())
        assert data["mode"] == "write"

    def test_stores_cwd(self, tmp_artifacts_dir):
        result = _run_result()
        aid = save_run_artifact(result, "hello", cwd="/tmp/test")
        data = json.loads((tmp_artifacts_dir / f"{aid}.json").read_text())
        assert data["cwd"] == "/tmp/test"


class TestSaveFanoutArtifact:
    def test_creates_file(self, tmp_artifacts_dir):
        results = [
            ("claude", _run_result(agent_id="claude")),
            ("codex", _run_result(agent_id="codex")),
        ]
        aid = save_fanout_artifact(results, "hello")
        assert aid.startswith("fanout-")
        path = tmp_artifacts_dir / f"{aid}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["type"] == "fanout"
        assert data["agents"] == ["claude", "codex"]
        assert len(data["results"]) == 2
        assert data["all_ok"] is True

    def test_records_failure(self, tmp_artifacts_dir):
        results = [
            ("claude", _run_result(agent_id="claude")),
            ("bad", FanoutError(agent_id="bad", error="Unknown agent")),
        ]
        aid = save_fanout_artifact(results, "hello")
        data = json.loads((tmp_artifacts_dir / f"{aid}.json").read_text())
        assert data["all_ok"] is False
        assert data["results"][1]["ok"] is False
        assert "error" in data["results"][1]


class TestSaveReviewArtifact:
    def test_creates_file(self, tmp_artifacts_dir):
        data = {
            "prompt": "Check this.",
            "results": [
                ("claude", _run_result(agent_id="claude")),
                ("codex", _run_result(agent_id="codex")),
            ],
            "judge": None,
        }
        aid = save_review_artifact(data)
        assert aid.startswith("review-")
        path = tmp_artifacts_dir / f"{aid}.json"
        assert path.exists()
        artifact = json.loads(path.read_text())
        assert artifact["type"] == "review"
        assert artifact["agents"] == ["claude", "codex"]
        assert artifact["prompt"] == "Check this."
        assert artifact["all_ok"] is True

    def test_with_judge(self, tmp_artifacts_dir):
        judge_data = {"agent": "claude", "ok": True, "stdout": "Good."}
        data = {
            "prompt": "Check.",
            "results": [("claude", _run_result(agent_id="claude"))],
            "judge": judge_data,
        }
        aid = save_review_artifact(data)
        artifact = json.loads((tmp_artifacts_dir / f"{aid}.json").read_text())
        assert artifact["judge"] == judge_data


class TestSaveDialecticArtifact:
    def test_creates_file(self, tmp_artifacts_dir):
        data = {
            "question": "Monorepos?",
            "thesis": ("claude", _run_result(agent_id="claude", stdout="Pro.")),
            "antithesis": ("codex", _run_result(agent_id="codex", stdout="Con.")),
            "synthesis": None,
        }
        aid = save_dialectic_artifact(data)
        assert aid.startswith("dialectic-")
        path = tmp_artifacts_dir / f"{aid}.json"
        assert path.exists()
        artifact = json.loads(path.read_text())
        assert artifact["type"] == "dialectic"
        assert artifact["agents"] == ["claude", "codex"]
        assert artifact["question"] == "Monorepos?"
        assert artifact["all_ok"] is True

    def test_with_synthesis(self, tmp_artifacts_dir):
        synthesis = {"agent": "claude", "ok": True, "stdout": "Balanced."}
        data = {
            "question": "Q?",
            "thesis": ("claude", _run_result(agent_id="claude")),
            "antithesis": ("codex", _run_result(agent_id="codex")),
            "synthesis": synthesis,
        }
        aid = save_dialectic_artifact(data)
        artifact = json.loads((tmp_artifacts_dir / f"{aid}.json").read_text())
        assert artifact["synthesis"] == synthesis


class TestSaveMatrixArtifact:
    def test_creates_file(self, tmp_artifacts_dir):
        rows = [
            {
                "prompt": "p1",
                "results": [
                    ("claude", _run_result(agent_id="claude")),
                    ("codex", _run_result(agent_id="codex")),
                ],
            },
            {
                "prompt": "p2",
                "results": [
                    ("claude", _run_result(agent_id="claude")),
                    ("codex", _run_result(agent_id="codex")),
                ],
            },
        ]
        aid = save_matrix_artifact(rows, ["claude", "codex"])
        assert aid.startswith("matrix-")
        path = tmp_artifacts_dir / f"{aid}.json"
        assert path.exists()
        artifact = json.loads(path.read_text())
        assert artifact["type"] == "matrix"
        assert artifact["agents"] == ["claude", "codex"]
        assert len(artifact["prompts"]) == 2
        assert artifact["all_ok"] is True

    def test_records_failure(self, tmp_artifacts_dir):
        rows = [{
            "prompt": "p1",
            "results": [
                ("bad", FanoutError(agent_id="bad", error="Unknown agent")),
            ],
        }]
        aid = save_matrix_artifact(rows, ["bad"])
        artifact = json.loads((tmp_artifacts_dir / f"{aid}.json").read_text())
        assert artifact["all_ok"] is False


class TestListArtifacts:
    def test_empty(self):
        assert list_artifacts() == []

    def test_lists_saved(self, tmp_artifacts_dir):
        r = _run_result()
        save_run_artifact(r, "one")
        save_run_artifact(r, "two")
        arts = list_artifacts()
        assert len(arts) == 2

    def test_newest_first(self, tmp_artifacts_dir):
        r = _run_result()
        aid1 = save_run_artifact(r, "first")
        # Manually adjust mtime to ensure ordering
        p1 = tmp_artifacts_dir / f"{aid1}.json"
        os.utime(p1, (0, 0))
        aid2 = save_run_artifact(_run_result(agent_id="codex"), "second")
        arts = list_artifacts()
        assert arts[0]["id"] == aid2

    def test_respects_limit(self, tmp_artifacts_dir):
        r = _run_result()
        for i in range(5):
            save_run_artifact(_run_result(agent_id=f"a{i}"), f"p{i}")
        arts = list_artifacts(limit=3)
        assert len(arts) == 3


class TestShowArtifact:
    def test_found(self, tmp_artifacts_dir):
        r = _run_result()
        aid = save_run_artifact(r, "hello")
        data = show_artifact(aid)
        assert data is not None
        assert data["id"] == aid

    def test_not_found(self):
        assert show_artifact("nonexistent-id") is None
