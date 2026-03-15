"""Tests for normalization helpers."""

from bashful.fanout import FanoutError
from bashful.normalize import normalize_fanout, normalize_run
from bashful.runner import RunResult


def _result(**overrides):
    defaults = dict(
        agent_id="claude",
        command=["claude", "-p", "hi"],
        stdout="hello world",
        stderr="",
        exit_code=0,
        duration_s=1.23,
        timed_out=False,
        mode="read",
    )
    defaults.update(overrides)
    return RunResult(**defaults)


class TestNormalizeRun:
    def test_basic_fields(self):
        r = _result()
        n = normalize_run(r)
        assert n["agent"] == "claude"
        assert n["ok"] is True
        assert n["timed_out"] is False
        assert n["exit_code"] == 0
        assert n["mode"] == "read"
        assert n["duration_s"] == 1.23

    def test_stdout_preview_truncated(self):
        r = _result(stdout="x" * 500)
        n = normalize_run(r, preview_len=100)
        assert len(n["stdout_preview"]) == 100

    def test_stderr_preview(self):
        r = _result(stderr="some error")
        n = normalize_run(r)
        assert n["stderr_preview"] == "some error"

    def test_timed_out(self):
        r = _result(timed_out=True, exit_code=-1)
        n = normalize_run(r)
        assert n["ok"] is False
        assert n["timed_out"] is True

    def test_failed(self):
        r = _result(exit_code=1)
        n = normalize_run(r)
        assert n["ok"] is False

    def test_strips_whitespace(self):
        r = _result(stdout="  hello  \n", stderr=" err \n")
        n = normalize_run(r)
        assert n["stdout_preview"] == "hello"
        assert n["stderr_preview"] == "err"


class TestNormalizeFanout:
    def test_all_ok(self):
        results = [
            ("claude", _result(agent_id="claude")),
            ("codex", _result(agent_id="codex")),
        ]
        s = normalize_fanout(results)
        assert s["all_ok"] is True
        assert s["count"] == 2
        assert len(s["results"]) == 2

    def test_mixed_with_error(self):
        results = [
            ("claude", _result(agent_id="claude")),
            ("bad", FanoutError(agent_id="bad", error="not found")),
        ]
        s = normalize_fanout(results)
        assert s["all_ok"] is False
        assert s["count"] == 2
        assert s["results"][1]["ok"] is False
        assert s["results"][1]["error"] == "not found"

    def test_empty(self):
        s = normalize_fanout([])
        assert s["all_ok"] is True
        assert s["count"] == 0
        assert s["results"] == []

    def test_error_item_fields(self):
        results = [
            ("x", FanoutError(agent_id="x", error="boom", timed_out=True)),
        ]
        s = normalize_fanout(results)
        item = s["results"][0]
        assert item["agent"] == "x"
        assert item["ok"] is False
        assert item["timed_out"] is True
        assert item["error"] == "boom"
        assert item["duration_s"] is None
