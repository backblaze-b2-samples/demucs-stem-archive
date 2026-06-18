from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# The four stems htdemucs produces, in display order.
StemRole = Literal["vocals", "drums", "bass", "other"]
STEM_ROLES: tuple[StemRole, ...] = ("vocals", "drums", "bass", "other")

# Lifecycle of a separation job. `pending` = enqueued, `processing` = demucs
# subprocess running, `done` = all 4 stems uploaded, `failed` = error captured.
SeparationStatus = Literal["pending", "processing", "done", "failed"]


class Stem(BaseModel):
    role: StemRole
    key: str
    size_bytes: int
    size_human: str
    # Present once the stem object exists in B2 (after separation finishes).
    uploaded_at: datetime | None = None


class TrackSummary(BaseModel):
    track_id: str
    title: str
    original_key: str
    original_size_bytes: int
    original_size_human: str
    uploaded_at: datetime
    status: SeparationStatus
    # Which stem roles already exist as objects in B2.
    stems_present: list[StemRole]
    stem_count: int
    error: str | None = None


class TrackDetail(TrackSummary):
    stems: list[Stem]


class ArchiveStats(BaseModel):
    track_count: int
    stem_count: int
    object_count: int
    total_size_bytes: int
    total_size_human: str
    # objects / originals — the write-amplification headline number.
    amplification_ratio: float
    separations_today: int
    processing_count: int
    failed_count: int


class DailyActivity(BaseModel):
    date: str
    tracks: int
    stems: int


class IngestResponse(BaseModel):
    track_id: str
    title: str
    original_key: str
    status: SeparationStatus
