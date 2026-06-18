import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def isolate_download_counter(tmp_path, monkeypatch):
    """Redirect the persisted download counter to a temp file per test and
    reset the in-memory counter to 0. Keeps tests hermetic and prevents
    stray writes to services/api/data/."""
    from app.config import settings
    from app.service import files as files_service

    counter_path = tmp_path / "download_count.json"
    monkeypatch.setattr(settings, "download_count_file", str(counter_path))
    monkeypatch.setattr(files_service, "_download_count", 0)
    yield


@pytest.fixture(autouse=True)
def mock_demucs(monkeypatch):
    """Never run the real Demucs subprocess (torch) in tests.

    We patch `_run_demucs` so the worker logic, B2 uploads, and job-state
    transitions are still exercised end-to-end — only the actual model run
    is replaced. Stem WAVs are written as tiny placeholder files into the
    output layout demucs would produce, and `upload_file` is stubbed so no
    real S3 call happens.
    """
    from pathlib import Path

    from app.service import separation

    def fake_run_demucs(input_path: Path, out_dir: Path) -> Path:
        stem_dir = out_dir / separation.settings.demucs_model / input_path.stem
        stem_dir.mkdir(parents=True, exist_ok=True)
        for role in separation.STEM_ROLES:
            (stem_dir / f"{role}.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        return stem_dir

    monkeypatch.setattr(separation, "_run_demucs", fake_run_demucs)

    uploaded: list[str] = []

    def fake_upload(file_data, key, content_type):
        uploaded.append(key)
        from datetime import UTC, datetime

        from app.types import FileMetadata

        return FileMetadata(
            key=key,
            filename=key.rsplit("/", 1)[-1],
            folder=key.rsplit("/", 1)[0] + "/",
            size_bytes=len(file_data),
            size_human="1 B",
            content_type=content_type,
            uploaded_at=datetime.now(UTC),
            url=None,
        )

    # Patch the symbols imported into each consuming module.
    monkeypatch.setattr(separation, "upload_file", fake_upload)
    from app.service import ingest as ingest_service

    monkeypatch.setattr(ingest_service, "upload_file", fake_upload)
    yield uploaded
