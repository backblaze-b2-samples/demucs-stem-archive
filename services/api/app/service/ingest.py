"""Audio-track ingest: validate, archive the original to B2, enqueue Demucs.

Adapted from the starter kit's generic upload service and specialized to
audio. The original is archived under `tracks/<track_id>/original/<safe_name>`
and a separation job is enqueued (the heavy work runs in a background thread
via service.separation — this call returns immediately).
"""

import re
import uuid

from app.config import settings
from app.repo import upload_file
from app.service.separation import enqueue_separation
from app.types import IngestResponse
from app.types.formatting import humanize_bytes

# Audio-only allowlist: MP3, WAV, FLAC (+ common aliases).
ALLOWED_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/flac",
    "audio/x-flac",
}

MIME_EXTENSION_MAP: dict[str, set[str]] = {
    "audio/mpeg": {"mp3", "mpeg"},
    "audio/mp3": {"mp3"},
    "audio/wav": {"wav"},
    "audio/x-wav": {"wav"},
    "audio/wave": {"wav"},
    "audio/flac": {"flac"},
    "audio/x-flac": {"flac"},
}

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def sanitize_filename(filename: str) -> str:
    """Strip path components, remove unsafe chars, limit length."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = _SAFE_FILENAME_RE.sub("_", name)
    name = re.sub(r"[_.]{2,}", "_", name)
    name = name.lstrip(".").strip()
    if len(name) > 200:
        base, _, ext = name.rpartition(".")
        name = base[: 200 - len(ext) - 1] + "." + ext if ext else name[:200]
    return name or "unnamed"


def make_track_id(filename: str) -> str:
    """`<slug-of-filename>-<uuid4 hex[:8]>` — human-browsable + collision-safe."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    slug = _SLUG_RE.sub("-", stem.lower()).strip("-")[:48] or "track"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def validate_extension_matches_type(filename: str, content_type: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_exts = MIME_EXTENSION_MAP.get(content_type)
    if allowed_exts is None:
        return False
    if not ext:
        return True
    return ext in allowed_exts


class IngestError(Exception):
    """Raised when ingest validation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def process_ingest(
    file_data: bytes,
    filename: str,
    content_type: str,
    content_length: int | None = None,
) -> IngestResponse:
    """Validate an audio track, archive the original, and enqueue separation."""
    if not filename:
        raise IngestError("No filename provided")

    if content_length and content_length > settings.max_file_size:
        raise IngestError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    if content_type not in ALLOWED_TYPES:
        raise IngestError(
            f"Unsupported audio type '{content_type}'. Use MP3, WAV, or FLAC.",
            status_code=415,
        )

    safe_name = sanitize_filename(filename)

    if not validate_extension_matches_type(safe_name, content_type):
        raise IngestError(
            "File extension does not match declared content type",
            status_code=415,
        )

    if len(file_data) == 0:
        raise IngestError("Empty file")

    if len(file_data) > settings.max_file_size:
        raise IngestError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    track_id = make_track_id(safe_name)
    original_key = f"{settings.tracks_prefix}{track_id}/original/{safe_name}"
    upload_file(file_data, original_key, content_type)

    # Enqueue Demucs on the in-memory worker. The bytes are handed straight
    # to the worker (no re-download) for the primary ingest path.
    enqueue_separation(track_id, safe_name, file_data)

    return IngestResponse(
        track_id=track_id,
        title=safe_name,
        original_key=original_key,
        status="pending",
    )
