"""Tests for audio-track ingest validation and enqueue behavior."""

from io import BytesIO

import pytest

from app.service import ingest as ingest_service
from app.service.ingest import (
    IngestError,
    make_track_id,
    process_ingest,
    sanitize_filename,
    validate_extension_matches_type,
)


def test_make_track_id_is_slug_plus_hex():
    tid = make_track_id("My Song (Final).mp3")
    # slug-of-filename + "-" + 8 hex chars
    assert tid.startswith("my-song-final-")
    suffix = tid.rsplit("-", 1)[-1]
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_sanitize_filename_strips_paths():
    # Only the final path component survives — directory parts are dropped.
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a/b/song.mp3") == "song.mp3"
    assert sanitize_filename("..\\..\\windows\\evil.mp3") == "evil.mp3"


def test_extension_must_match_audio_type():
    assert validate_extension_matches_type("song.mp3", "audio/mpeg")
    assert validate_extension_matches_type("song.wav", "audio/wav")
    assert validate_extension_matches_type("song.flac", "audio/flac")
    assert not validate_extension_matches_type("song.png", "audio/mpeg")


def test_ingest_rejects_non_audio(monkeypatch):
    enqueued: list[str] = []
    monkeypatch.setattr(
        ingest_service, "enqueue_separation",
        lambda track_id, name, data: enqueued.append(track_id),
    )
    with pytest.raises(IngestError) as exc:
        process_ingest(
            file_data=b"not audio",
            filename="photo.png",
            content_type="image/png",
        )
    assert exc.value.status_code == 415
    assert enqueued == []


def test_ingest_rejects_empty_file(monkeypatch):
    monkeypatch.setattr(
        ingest_service, "enqueue_separation", lambda *a, **k: None
    )
    with pytest.raises(IngestError) as exc:
        process_ingest(
            file_data=b"",
            filename="song.mp3",
            content_type="audio/mpeg",
        )
    assert "empty" in exc.value.detail.lower()


def test_ingest_archives_original_and_enqueues(monkeypatch):
    enqueued: list[tuple] = []
    monkeypatch.setattr(
        ingest_service, "enqueue_separation",
        lambda track_id, name, data: enqueued.append((track_id, name, data)),
    )
    result = process_ingest(
        file_data=b"ID3 fake mp3 bytes",
        filename="great track.mp3",
        content_type="audio/mpeg",
    )
    assert result.status == "pending"
    assert result.original_key.startswith("tracks/")
    assert result.original_key.endswith("/original/great_track.mp3")
    # A job was enqueued for this track with the raw bytes.
    assert len(enqueued) == 1
    assert enqueued[0][0] == result.track_id
    assert enqueued[0][2] == b"ID3 fake mp3 bytes"


@pytest.mark.asyncio
async def test_post_tracks_rejects_non_audio(client, monkeypatch):
    monkeypatch.setattr(
        ingest_service, "enqueue_separation", lambda *a, **k: None
    )
    response = await client.post(
        "/tracks",
        files={"file": ("photo.png", BytesIO(b"x"), "image/png")},
    )
    assert response.status_code == 415
