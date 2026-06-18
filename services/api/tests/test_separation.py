"""Tests for the Demucs separation worker.

The real demucs subprocess (torch) is NEVER run — `mock_demucs` in conftest
replaces `_run_demucs` with a stub that writes placeholder stem WAVs. These
tests exercise the worker's job-state machine and B2 upload calls.
"""

from app.service import separation
from app.types import STEM_ROLES


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
