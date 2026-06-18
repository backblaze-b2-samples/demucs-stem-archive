"""Local Demucs stem separation worker.

Demucs (and therefore torch) is run ONLY as a subprocess
(`python -m demucs ...`). Nothing in this module imports torch or demucs at
the top level, so `from main import app` and pytest collection stay fast and
work with only the light deps installed. The heavy model lives entirely in
the child process.

A small ThreadPoolExecutor owns the jobs so the ingest request returns
immediately while separation runs in the background. Job state is an
in-memory, thread-safe registry — durable artifacts always land in B2, so a
restart loses only transient status, never the stems themselves.
"""

import logging
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.config import settings
from app.repo import upload_file
from app.types import STEM_ROLES, SeparationStatus, StemRole

logger = logging.getLogger(__name__)

# One worker: htdemucs is CPU/GPU heavy and we don't want concurrent runs
# thrashing the machine. Jobs queue behind each other.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="demucs")


@dataclass
class SeparationJob:
    track_id: str
    status: SeparationStatus = "pending"
    stems_done: list[StemRole] = field(default_factory=list)
    error: str | None = None


_jobs: dict[str, SeparationJob] = {}
_jobs_lock = Lock()


def get_job(track_id: str) -> SeparationJob | None:
    with _jobs_lock:
        job = _jobs.get(track_id)
        if job is None:
            return None
        # Return a snapshot so callers never read a mutating object.
        return SeparationJob(
            track_id=job.track_id,
            status=job.status,
            stems_done=list(job.stems_done),
            error=job.error,
        )


def _set_status(track_id: str, status: SeparationStatus, error: str | None = None) -> None:
    with _jobs_lock:
        job = _jobs.setdefault(track_id, SeparationJob(track_id=track_id))
        job.status = status
        if error is not None:
            job.error = error


def _mark_stem_done(track_id: str, role: StemRole) -> None:
    with _jobs_lock:
        job = _jobs.setdefault(track_id, SeparationJob(track_id=track_id))
        if role not in job.stems_done:
            job.stems_done.append(role)


def enqueue_separation(track_id: str, source_name: str, audio: bytes) -> None:
    """Register a pending job and hand it to the worker pool."""
    with _jobs_lock:
        _jobs[track_id] = SeparationJob(track_id=track_id, status="pending")
    _executor.submit(_run_job, track_id, source_name, audio)


def _stem_key(track_id: str, role: StemRole) -> str:
    return f"{settings.tracks_prefix}{track_id}/stems/{role}.wav"


def _run_demucs(input_path: Path, out_dir: Path) -> Path:
    """Run demucs as a subprocess and return the directory holding the 4 WAVs.

    Layout demucs writes: <out_dir>/<model>/<input-stem>/<role>.wav
    """
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "-n",
        settings.demucs_model,
        "-d",
        settings.demucs_device,
        "--out",
        str(out_dir),
        str(input_path),
    ]
    logger.info("Running demucs: %s", " ".join(cmd))
    # Fixed argv, no shell — input/output paths are app-controlled temp paths.
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"demucs exited {result.returncode}: {result.stderr.strip()[-500:]}"
        )
    stem_dir = out_dir / settings.demucs_model / input_path.stem
    if not stem_dir.is_dir():
        raise RuntimeError(f"demucs produced no output at {stem_dir}")
    return stem_dir


def _run_job(track_id: str, source_name: str, audio: bytes) -> None:
    _set_status(track_id, "processing")
    tmp = Path(tempfile.mkdtemp(prefix="demucs-"))
    try:
        # Preserve the original extension so demucs/ffmpeg sniff the format.
        suffix = Path(source_name).suffix or ".wav"
        input_path = tmp / f"input{suffix}"
        input_path.write_bytes(audio)

        out_dir = tmp / "out"
        stem_dir = _run_demucs(input_path, out_dir)

        for role in STEM_ROLES:
            wav = stem_dir / f"{role}.wav"
            if not wav.is_file():
                raise RuntimeError(f"missing expected stem: {role}.wav")
            upload_file(wav.read_bytes(), _stem_key(track_id, role), "audio/wav")
            _mark_stem_done(track_id, role)

        _set_status(track_id, "done")
        logger.info("Separation complete: track_id=%s", track_id)
    except Exception as e:
        # Capture any failure into job state — never let the worker thread die.
        logger.error("Separation failed: track_id=%s err=%s", track_id, e, exc_info=True)
        _set_status(track_id, "failed", error=str(e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
