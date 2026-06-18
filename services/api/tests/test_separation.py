"""Tests for the Demucs separation worker.

The real demucs subprocess (torch) is NEVER run — `mock_demucs` in conftest
replaces `_run_demucs` with a stub that writes placeholder stem WAVs. These
tests exercise the worker's job-state machine and B2 upload calls.
"""

from pathlib import Path

from app.config import settings
from app.service import separation
from app.types import STEM_ROLES

# The autouse `mock_demucs` fixture swaps out `_run_demucs` entirely. To test
# the real subprocess-arg construction we keep a reference to the genuine
# implementation captured at import time, before any fixture patches it.
_REAL_RUN_DEMUCS = separation._run_demucs


def _capture_demucs_cmd(monkeypatch, tmp_path: Path) -> list[str]:
    """Run the real `_run_demucs` with subprocess.run stubbed; return the argv.

    The stub also lays down the 4 stem WAVs so `_run_demucs` returns cleanly.
    """
    captured: dict[str, list[str]] = {}

    class FakeResult:
        returncode = 0
        stderr = ""

    def fake_run(cmd, capture_output, text):
        captured["cmd"] = cmd
        stem_dir = tmp_path / "out" / settings.demucs_model / "input"
        stem_dir.mkdir(parents=True, exist_ok=True)
        for role in STEM_ROLES:
            (stem_dir / f"{role}.wav").write_bytes(b"RIFF")
        return FakeResult()

    # Restore the real implementation (autouse mock_demucs replaced it).
    monkeypatch.setattr(separation, "_run_demucs", _REAL_RUN_DEMUCS)
    monkeypatch.setattr(separation.subprocess, "run", fake_run)
    _REAL_RUN_DEMUCS(tmp_path / "input.wav", tmp_path / "out")
    return captured["cmd"]


def test_demucs_cmd_omits_device_flag_when_auto(monkeypatch, tmp_path):
    # "auto" is the shipped default; demucs has no "auto" device, so -d must
    # be omitted entirely (demucs then auto-detects cuda-else-cpu).
    monkeypatch.setattr(settings, "demucs_device", "auto")
    cmd = _capture_demucs_cmd(monkeypatch, tmp_path)
    assert "-d" not in cmd
    assert "auto" not in cmd


def test_demucs_cmd_passes_explicit_device(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "demucs_device", "cpu")
    cmd = _capture_demucs_cmd(monkeypatch, tmp_path)
    assert "-d" in cmd
    assert cmd[cmd.index("-d") + 1] == "cpu"


def test_run_job_uploads_four_stems_and_marks_done(mock_demucs):
    track_id = "song-deadbeef"
    separation._run_job(track_id, "song.mp3", b"fake audio bytes")

    job = separation.get_job(track_id)
    assert job is not None
    assert job.status == "done"
    assert set(job.stems_done) == set(STEM_ROLES)

    # mock_demucs yields the list of uploaded keys.
    stem_keys = [k for k in mock_demucs if "/stems/" in k]
    assert len(stem_keys) == 4
    for role in STEM_ROLES:
        assert any(k.endswith(f"/stems/{role}.wav") for k in stem_keys)


def test_run_job_captures_failure(monkeypatch):
    def boom(input_path, out_dir):
        raise RuntimeError("demucs exited 1: boom")

    monkeypatch.setattr(separation, "_run_demucs", boom)
    track_id = "song-cafebabe"
    separation._run_job(track_id, "song.mp3", b"fake")

    job = separation.get_job(track_id)
    assert job is not None
    assert job.status == "failed"
    assert "boom" in (job.error or "")


def test_enqueue_separation_registers_pending(monkeypatch):
    submitted: list[str] = []

    class FakeFuture:
        pass

    monkeypatch.setattr(
        separation._executor,
        "submit",
        lambda fn, *args: submitted.append(args[0]) or FakeFuture(),
    )
    separation.enqueue_separation("song-12345678", "song.mp3", b"x")
    job = separation.get_job("song-12345678")
    assert job is not None
    assert job.status == "pending"
    assert submitted == ["song-12345678"]
