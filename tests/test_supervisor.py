"""Tests for process supervision."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from bashful.agents import AgentInfo, HeadlessProfile
from bashful.supervisor import (
    Job,
    JobStatus,
    _handles,
    kill_job,
    launch,
    list_jobs,
    poll,
    read_logs,
    wait_for_job,
    watch_job,
)


def _agent():
    return AgentInfo(
        id="test",
        name="Test Agent",
        executable="test-agent",
        description="test",
        invocation="test-agent -p 'hi'",
        headless=HeadlessProfile(style="flag", args=["-p", "{prompt}"]),
        version_args=["--version"],
    )


@pytest.fixture(autouse=True)
def clean_handles():
    """Clear in-session handles between tests."""
    _handles.clear()
    yield
    _handles.clear()


class TestLaunch:
    def test_creates_job_directory(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "hello world", jobs_dir=tmp_path)

        assert (tmp_path / job.job_id).is_dir()
        assert (tmp_path / job.job_id / "meta.json").exists()
        assert (tmp_path / job.job_id / "stdout.log").exists()
        assert (tmp_path / job.job_id / "stderr.log").exists()

    def test_job_fields(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 42

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "test prompt", jobs_dir=tmp_path)

        assert job.agent_id == "test"
        assert job.prompt == "test prompt"
        assert job.pid == 42
        assert "/usr/bin/test-agent" in job.command[0]

    def test_meta_json_content(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 99

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "meta test", jobs_dir=tmp_path)

        meta = json.loads((tmp_path / job.job_id / "meta.json").read_text())
        assert meta["agent_id"] == "test"
        assert meta["prompt"] == "meta test"
        assert meta["pid"] == 99

    def test_no_headless_raises(self, tmp_path):
        agent = AgentInfo(
            id="bad", name="Bad", executable="bad",
            description="no headless", invocation="bad",
        )
        with pytest.raises(ValueError, match="no headless"):
            launch(agent, "hi", jobs_dir=tmp_path)

    def test_not_installed_raises(self, tmp_path):
        agent = _agent()
        with patch("bashful.supervisor.shutil.which", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                launch(agent, "hi", jobs_dir=tmp_path)

    def test_stores_popen_handle(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 1

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "handle test", jobs_dir=tmp_path)

        assert job.job_id in _handles


class TestPoll:
    def test_running_job(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 10
        mock_proc.poll.return_value = None  # Still running

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "running", jobs_dir=tmp_path)

        status = poll(job.job_id, jobs_dir=tmp_path)
        assert status.state == "running"
        assert status.exit_code is None

    def test_completed_job(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 10
        mock_proc.poll.return_value = 0

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "done", jobs_dir=tmp_path)

        status = poll(job.job_id, jobs_dir=tmp_path)
        assert status.state == "completed"
        assert status.exit_code == 0

    def test_failed_job(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 10
        mock_proc.poll.return_value = 1

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "fail", jobs_dir=tmp_path)

        status = poll(job.job_id, jobs_dir=tmp_path)
        assert status.state == "failed"
        assert status.exit_code == 1

    def test_cross_session_dead_pid(self, tmp_path):
        """Job from a previous session (no Popen handle), PID is dead."""
        job_dir = tmp_path / "deadjob"
        job_dir.mkdir()
        meta = {
            "job_id": "deadjob",
            "agent_id": "test",
            "prompt": "old",
            "pid": 999999,
            "command": ["test"],
            "cwd": "/tmp",
            "started_at": time.time() - 100,
        }
        (job_dir / "meta.json").write_text(json.dumps(meta))

        with patch("bashful.supervisor._pid_alive", return_value=False):
            status = poll("deadjob", jobs_dir=tmp_path)

        assert status.state == "lost"

    def test_cross_session_alive_pid_reports_unknown(self, tmp_path):
        """Job from previous session with alive PID → unknown (can't trust PID)."""
        job_dir = tmp_path / "alivejob"
        job_dir.mkdir()
        meta = {
            "job_id": "alivejob",
            "agent_id": "test",
            "prompt": "old",
            "pid": 999999,
            "command": ["test"],
            "cwd": "/tmp",
            "started_at": time.time() - 100,
        }
        (job_dir / "meta.json").write_text(json.dumps(meta))

        with patch("bashful.supervisor._pid_alive", return_value=True):
            status = poll("alivejob", jobs_dir=tmp_path)

        assert status.state == "unknown"

    def test_status_file_cached(self, tmp_path):
        """Once status.json is written, it's used directly."""
        job_dir = tmp_path / "cached"
        job_dir.mkdir()
        meta = {
            "job_id": "cached",
            "agent_id": "test",
            "prompt": "cached",
            "pid": 1,
            "command": ["test"],
            "cwd": "/tmp",
            "started_at": 1000.0,
        }
        (job_dir / "meta.json").write_text(json.dumps(meta))
        (job_dir / "status.json").write_text(json.dumps({
            "state": "killed",
            "exit_code": None,
            "ended_at": 1010.0,
        }))

        status = poll("cached", jobs_dir=tmp_path)
        assert status.state == "killed"
        assert status.duration_s == 10.0

    def test_not_found(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            poll("nonexistent", jobs_dir=tmp_path)


class TestListJobs:
    def test_empty(self, tmp_path):
        assert list_jobs(jobs_dir=tmp_path) == []

    def test_lists_jobs(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 1
        mock_proc.poll.return_value = 0

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            launch(agent, "job1", jobs_dir=tmp_path)
            launch(agent, "job2", jobs_dir=tmp_path)

        jobs = list_jobs(jobs_dir=tmp_path)
        assert len(jobs) == 2

    def test_filter_by_state(self, tmp_path):
        agent = _agent()

        # Running job
        running_proc = MagicMock()
        running_proc.pid = 1
        running_proc.poll.return_value = None

        # Completed job
        done_proc = MagicMock()
        done_proc.pid = 2
        done_proc.poll.return_value = 0

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", side_effect=[running_proc, done_proc]),
        ):
            launch(agent, "running", jobs_dir=tmp_path)
            launch(agent, "done", jobs_dir=tmp_path)

        running = list_jobs(state_filter="running", jobs_dir=tmp_path)
        completed = list_jobs(state_filter="completed", jobs_dir=tmp_path)
        assert len(running) == 1
        assert len(completed) == 1


class TestKillJob:
    def test_kill_running(self, tmp_path):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 1
        mock_proc.poll.return_value = None
        mock_proc.returncode = -15

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "kill me", jobs_dir=tmp_path)

        killed = kill_job(job.job_id, jobs_dir=tmp_path)
        assert killed
        mock_proc.terminate.assert_called_once()

    def test_cross_session_kill_refused(self, tmp_path):
        """Cross-session kill (PID only) should be refused for safety."""
        job_dir = tmp_path / "crossjob"
        job_dir.mkdir()
        (job_dir / "meta.json").write_text(json.dumps({
            "job_id": "crossjob", "agent_id": "t", "prompt": "t",
            "pid": 999999, "command": [], "cwd": "/", "started_at": 0,
        }))

        # No Popen handle, PID alive — should refuse to kill
        with patch("bashful.supervisor._pid_alive", return_value=True):
            killed = kill_job("crossjob", jobs_dir=tmp_path)
        assert not killed

    def test_kill_already_done(self, tmp_path):
        job_dir = tmp_path / "done"
        job_dir.mkdir()
        (job_dir / "meta.json").write_text(json.dumps({
            "job_id": "done", "agent_id": "t", "prompt": "t",
            "pid": 1, "command": [], "cwd": "/", "started_at": 0,
        }))
        (job_dir / "status.json").write_text(json.dumps({
            "state": "completed", "exit_code": 0, "ended_at": 1,
        }))

        killed = kill_job("done", jobs_dir=tmp_path)
        assert not killed


class TestReadLogs:
    def test_read_stdout(self, tmp_path):
        job_dir = tmp_path / "logtest"
        job_dir.mkdir()
        (job_dir / "stdout.log").write_text("line1\nline2\nline3\n")

        content = read_logs("logtest", jobs_dir=tmp_path)
        assert "line1" in content
        assert "line3" in content

    def test_read_stderr(self, tmp_path):
        job_dir = tmp_path / "logtest2"
        job_dir.mkdir()
        (job_dir / "stderr.log").write_text("error output\n")

        content = read_logs("logtest2", stream="stderr", jobs_dir=tmp_path)
        assert "error output" in content

    def test_tail(self, tmp_path):
        job_dir = tmp_path / "tailtest"
        job_dir.mkdir()
        (job_dir / "stdout.log").write_text("a\nb\nc\nd\ne\n")

        content = read_logs("tailtest", tail=2, jobs_dir=tmp_path)
        lines = content.strip().splitlines()
        assert lines == ["d", "e"]

    def test_not_found(self, tmp_path):
        with pytest.raises(ValueError, match="No stdout log"):
            read_logs("nope", jobs_dir=tmp_path)


class TestWaitForJob:
    def test_wait_already_done(self, tmp_path):
        """wait_for_job returns immediately for a finished job."""
        job_dir = tmp_path / "done"
        job_dir.mkdir()
        (job_dir / "meta.json").write_text(json.dumps({
            "job_id": "done", "agent_id": "test", "prompt": "t",
            "pid": 1, "command": [], "cwd": "/", "started_at": 100.0,
        }))
        (job_dir / "status.json").write_text(json.dumps({
            "state": "completed", "exit_code": 0, "ended_at": 110.0,
        }))

        status = wait_for_job("done", interval=0.01, jobs_dir=tmp_path)
        assert status.state == "completed"
        assert status.exit_code == 0

    def test_wait_transitions_to_done(self, tmp_path):
        """wait_for_job polls until the job finishes."""
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.pid = 10
        # First poll: still running.  Second poll: done.
        mock_proc.poll.side_effect = [None, 0]

        with (
            patch("bashful.supervisor.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.supervisor.subprocess.Popen", return_value=mock_proc),
        ):
            job = launch(agent, "wait-test", jobs_dir=tmp_path)

        status = wait_for_job(job.job_id, interval=0.01, jobs_dir=tmp_path)
        assert status.state == "completed"

    def test_wait_not_found(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            wait_for_job("nope", jobs_dir=tmp_path)


class TestWatchJob:
    def test_watch_completed(self, tmp_path, capsys):
        """watch_job streams output then returns status."""
        job_dir = tmp_path / "wjob"
        job_dir.mkdir()
        (job_dir / "meta.json").write_text(json.dumps({
            "job_id": "wjob", "agent_id": "test", "prompt": "t",
            "pid": 1, "command": [], "cwd": "/", "started_at": 100.0,
        }))
        (job_dir / "status.json").write_text(json.dumps({
            "state": "completed", "exit_code": 0, "ended_at": 110.0,
        }))
        (job_dir / "stdout.log").write_text("line one\nline two\n")

        status = watch_job("wjob", interval=0.01, jobs_dir=tmp_path)
        assert status.state == "completed"
        captured = capsys.readouterr().out
        assert "line one" in captured
        assert "line two" in captured
