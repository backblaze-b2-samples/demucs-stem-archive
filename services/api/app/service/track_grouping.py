"""Group flat B2 object keys under `tracks/` into per-track records.

Key layout written by ingest + separation:
    tracks/<track_id>/original/<safe_filename>
    tracks/<track_id>/stems/<role>.wav

This module is pure key/metadata wrangling — no S3, no job state — so it is
trivially unit-testable.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from app.types import STEM_ROLES, FileMetadata, StemRole

_STEM_FILE_RE = re.compile(r"^(vocals|drums|bass|other)\.wav$")


@dataclass
class StemObject:
    role: StemRole
    key: str
    size_bytes: int
    uploaded_at: datetime


@dataclass
class RawTrack:
    track_id: str
    original: FileMetadata | None = None
    stems: dict[StemRole, StemObject] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return self.original.filename if self.original else self.track_id

    @property
    def stems_present(self) -> list[StemRole]:
        # Stable display order.
        return [r for r in STEM_ROLES if r in self.stems]


def _parse_key(prefix: str, key: str) -> tuple[str, str, str] | None:
    """Return (track_id, kind, leaf) for a key under the tracks prefix.

    kind is "original" or "stems"; returns None for keys that don't fit the
    expected layout (e.g. stray objects).
    """
    if not key.startswith(prefix):
        return None
    rest = key[len(prefix):]
    parts = rest.split("/")
    if len(parts) != 3:
        return None
    track_id, kind, leaf = parts
    if not track_id or kind not in ("original", "stems") or not leaf:
        return None
    return track_id, kind, leaf


def group_tracks(prefix: str, files: list[FileMetadata]) -> dict[str, RawTrack]:
    """Group a flat list of FileMetadata into RawTrack records keyed by id."""
    tracks: dict[str, RawTrack] = {}
    for f in files:
        parsed = _parse_key(prefix, f.key)
        if parsed is None:
            continue
        track_id, kind, leaf = parsed
        track = tracks.setdefault(track_id, RawTrack(track_id=track_id))
        if kind == "original":
            track.original = f
        elif kind == "stems":
            m = _STEM_FILE_RE.match(leaf)
            if m:
                role: StemRole = m.group(1)  # type: ignore[assignment]
                track.stems[role] = StemObject(
                    role=role,
                    key=f.key,
                    size_bytes=f.size_bytes,
                    uploaded_at=f.uploaded_at,
                )
    return tracks
