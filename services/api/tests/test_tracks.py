"""Tests for the tracks domain service: grouping, stats, scoped delete."""

from datetime import UTC, datetime, timedelta

import pytest

from app.service import tracks as tracks_service
from app.service.track_grouping import group_tracks
from app.types import FileMetadata


def _file(key: str, size: int = 1000, hours_ago: int = 0) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.rsplit("/", 1)[-1],
        folder=key.rsplit("/", 1)[0] + "/",
        size_bytes=size,
        size_human=f"{size} B",
        content_type="audio/wav",
        uploaded_at=datetime.now(UTC) - timedelta(hours=hours_ago),
        url=None,
    )


def _full_track_files(track_id: str) -> list[FileMetadata]:
    return [
        _file(f"tracks/{track_id}/original/song.mp3", size=5000),
        _file(f"tracks/{track_id}/stems/vocals.wav", size=2000),
        _file(f"tracks/{track_id}/stems/drums.wav", size=2000),
        _file(f"tracks/{track_id}/stems/bass.wav", size=2000),
        _file(f"tracks/{track_id}/stems/other.wav", size=2000),
    ]


def test_group_tracks_groups_original_and_stems():
    files = _full_track_files("song-abc12345")
    # Add a stray object that doesn't fit the layout — must be ignored.
    files.append(_file("tracks/loose-object.txt"))
    grouped = group_tracks("tracks/", files)
    assert set(grouped) == {"song-abc12345"}
    raw = grouped["song-abc12345"]
    assert raw.original is not None
    assert raw.stems_present == ["vocals", "drums", "bass", "other"]


def test_list_tracks_overlays_done_status(monkeypatch):
    files = _full_track_files("song-abc12345")
    monkeypatch.setattr(tracks_service, "list_files", lambda prefix, max_keys: files)
    monkeypatch.setattr(tracks_service, "get_job", lambda track_id: None)
    summaries = tracks_service.list_tracks()
    assert len(summaries) == 1
    assert summaries[0].status == "done"
    assert summaries[0].stem_count == 4


def test_archive_stats_amplification_math(monkeypatch):
    # Two fully-separated tracks => 10 objects / 2 originals = 5.0 ratio.
    files = _full_track_files("a-1") + _full_track_files("b-2")
    monkeypatch.setattr(tracks_service, "list_files", lambda prefix, max_keys: files)
    monkeypatch.setattr(tracks_service, "get_job", lambda track_id: None)
    stats = tracks_service.get_archive_stats()
    assert stats.track_count == 2
    assert stats.stem_count == 8
    assert stats.object_count == 10
    assert stats.amplification_ratio == 5.0


def test_validate_track_id_rejects_traversal():
    from app.service.tracks import TrackKeyError, validate_track_id

    for bad in ["", "../etc", "a/../b", "Bad ID", "a%2e%2e"]:
        with pytest.raises(TrackKeyError):
            validate_track_id(bad)
    validate_track_id("song-abc12345")


def test_delete_track_is_scoped_to_prefix(monkeypatch):
    deleted: list[str] = []
    track_files = _full_track_files("song-abc12345")
    # list_files is called with the track prefix; return only that track's keys.
    monkeypatch.setattr(
        tracks_service, "list_files", lambda prefix, max_keys: track_files
    )
    monkeypatch.setattr(tracks_service, "delete_file", lambda key: deleted.append(key))

    count = tracks_service.delete_track("song-abc12345")
    assert count == 5
    # Every deleted key is scoped under this track's prefix — never anything else.
    assert all(k.startswith("tracks/song-abc12345/") for k in deleted)


@pytest.mark.asyncio
async def test_delete_track_endpoint_404_when_empty(client, monkeypatch):
    monkeypatch.setattr(tracks_service, "list_files", lambda prefix, max_keys: [])
    response = await client.delete("/tracks/missing-track1")
    assert response.status_code == 404
