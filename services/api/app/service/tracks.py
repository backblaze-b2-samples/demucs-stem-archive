"""Tracks domain service: library listing, archive stats, scoped delete.

Builds the scoped Stem Library view on top of the flat B2 object list,
overlaying live separation-job status, and computes the write-amplification
metrics (objects / originals) the dashboard surfaces.
"""

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.repo import delete_file, list_files
from app.service.separation import get_job
from app.service.track_grouping import RawTrack, group_tracks
from app.types import (
    STEM_ROLES,
    ArchiveStats,
    DailyActivity,
    SeparationStatus,
    Stem,
    TrackDetail,
    TrackSummary,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

_DANGEROUS_KEY_RE = re.compile(r"(\.\./|/\.\.|\\|%2e%2e|%00|\x00)")
_TRACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


class TrackKeyError(Exception):
    def __init__(self, detail: str = "Invalid track id"):
        self.detail = detail
        super().__init__(detail)


class TrackNotFoundError(Exception):
    def __init__(self, detail: str = "Track not found"):
        self.detail = detail
        super().__init__(detail)


def validate_track_id(track_id: str) -> None:
    if not track_id or _DANGEROUS_KEY_RE.search(track_id.lower()):
        raise TrackKeyError()
    if not _TRACK_ID_RE.match(track_id):
        raise TrackKeyError()


def _derive_status(raw: RawTrack) -> tuple[SeparationStatus, str | None]:
    """Live job status wins; otherwise infer from objects present in B2."""
    job = get_job(raw.track_id)
    if job is not None and job.status in ("pending", "processing", "failed"):
        return job.status, job.error
    if len(raw.stems) == len(STEM_ROLES):
        return "done", None
    if raw.stems:
        # Some stems present but not all and no live job — treat as processing
        # so a restart mid-run still reads sensibly.
        return "processing", None
    if job is not None:
        return job.status, job.error
    return "pending", None


def _to_summary(raw: RawTrack) -> TrackSummary:
    status, error = _derive_status(raw)
    original = raw.original
    return TrackSummary(
        track_id=raw.track_id,
        title=raw.title,
        original_key=original.key if original else "",
        original_size_bytes=original.size_bytes if original else 0,
        original_size_human=original.size_human if original else "0 B",
        uploaded_at=original.uploaded_at if original else datetime.now(UTC),
        status=status,
        stems_present=raw.stems_present,
        stem_count=len(raw.stems),
        error=error,
    )


def _load_raw_tracks() -> dict[str, RawTrack]:
    files = list_files(prefix=settings.tracks_prefix, max_keys=1000)
    return group_tracks(settings.tracks_prefix, files)


def list_tracks() -> list[TrackSummary]:
    tracks = _load_raw_tracks()
    summaries = [_to_summary(t) for t in tracks.values()]
    summaries.sort(key=lambda s: s.uploaded_at, reverse=True)
    return summaries


def get_track(track_id: str) -> TrackDetail:
    validate_track_id(track_id)
    tracks = _load_raw_tracks()
    raw = tracks.get(track_id)
    if raw is None:
        raise TrackNotFoundError()
    summary = _to_summary(raw)
    stems = [
        Stem(
            role=s.role,
            key=s.key,
            size_bytes=s.size_bytes,
            size_human=humanize_bytes(s.size_bytes),
            uploaded_at=s.uploaded_at,
        )
        for s in (raw.stems[r] for r in raw.stems_present)
    ]
    return TrackDetail(**summary.model_dump(), stems=stems)


def delete_track(track_id: str) -> int:
    """Delete every object under tracks/<track_id>/ — scoped, never broad.

    Returns the number of objects deleted.
    """
    validate_track_id(track_id)
    track_prefix = f"{settings.tracks_prefix}{track_id}/"
    objects = list_files(prefix=track_prefix, max_keys=1000)
    if not objects:
        raise TrackNotFoundError()
    deleted = 0
    for obj in objects:
        # Defense-in-depth: never delete anything outside this track's prefix.
        if not obj.key.startswith(track_prefix):
            continue
        delete_file(obj.key)
        deleted += 1
    logger.info("Track deleted: track_id=%s objects=%d", track_id, deleted)
    return deleted


def get_archive_stats() -> ArchiveStats:
    tracks = _load_raw_tracks()
    files = list_files(prefix=settings.tracks_prefix, max_keys=1000)

    object_count = len(files)
    total_size = sum(f.size_bytes for f in files)
    track_count = len(tracks)
    stem_count = sum(len(t.stems) for t in tracks.values())

    ratio = (object_count / track_count) if track_count else 0.0

    today = datetime.now(UTC).date()
    separations_today = sum(
        1
        for t in tracks.values()
        if t.original and t.original.uploaded_at.date() == today
    )

    processing = 0
    failed = 0
    for t in tracks.values():
        status, _ = _derive_status(t)
        if status in ("pending", "processing"):
            processing += 1
        elif status == "failed":
            failed += 1

    return ArchiveStats(
        track_count=track_count,
        stem_count=stem_count,
        object_count=object_count,
        total_size_bytes=total_size,
        total_size_human=humanize_bytes(total_size),
        amplification_ratio=round(ratio, 2),
        separations_today=separations_today,
        processing_count=processing,
        failed_count=failed,
    )


def get_activity(days: int = 7) -> list[DailyActivity]:
    """Tracks ingested + stems produced per day, for the last N days."""
    files = list_files(prefix=settings.tracks_prefix, max_keys=1000)
    grouped = group_tracks(settings.tracks_prefix, files)

    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)

    track_counts: dict[str, int] = defaultdict(int)
    stem_counts: dict[str, int] = defaultdict(int)
    for raw in grouped.values():
        if raw.original:
            d = raw.original.uploaded_at.date()
            if d >= cutoff:
                track_counts[d.isoformat()] += 1
        for stem in raw.stems.values():
            d = stem.uploaded_at.date()
            if d >= cutoff:
                stem_counts[d.isoformat()] += 1

    out: list[DailyActivity] = []
    for i in range(days):
        iso = (cutoff + timedelta(days=i)).isoformat()
        out.append(
            DailyActivity(
                date=iso,
                tracks=track_counts.get(iso, 0),
                stems=stem_counts.get(iso, 0),
            )
        )
    return out
