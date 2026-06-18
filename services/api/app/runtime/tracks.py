import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile

from app.config import settings
from app.runtime.metrics import record_upload
from app.service.ingest import IngestError, process_ingest
from app.service.tracks import (
    TrackKeyError,
    TrackNotFoundError,
    delete_track,
    get_activity,
    get_archive_stats,
    get_track,
    list_tracks,
)
from app.types import (
    ArchiveStats,
    DailyActivity,
    IngestResponse,
    TrackDetail,
    TrackSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tracks", response_model=IngestResponse)
async def ingest_track(request: Request, file: UploadFile):
    content_type = file.content_type or "application/octet-stream"
    content_length_header = request.headers.get("content-length")
    content_length = int(content_length_header) if content_length_header else None

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    file_data = b"".join(chunks)

    try:
        result = process_ingest(
            file_data=file_data,
            filename=file.filename or "",
            content_type=content_type,
            content_length=content_length,
        )
    except IngestError as e:
        logger.warning("Ingest rejected: %s", e.detail)
        record_upload(success=False)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

    record_upload(success=True)
    logger.info(
        "Track ingested: track_id=%s key=%s size=%d",
        result.track_id,
        result.original_key,
        len(file_data),
    )
    return result


@router.get("/tracks", response_model=list[TrackSummary])
async def list_tracks_endpoint():
    return list_tracks()


@router.get("/tracks/stats", response_model=ArchiveStats)
async def archive_stats_endpoint():
    return get_archive_stats()


@router.get("/tracks/stats/activity", response_model=list[DailyActivity])
async def activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_activity(days=days)


@router.get("/tracks/{track_id}", response_model=TrackDetail)
async def get_track_endpoint(track_id: str):
    try:
        return get_track(track_id)
    except TrackKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except TrackNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.delete("/tracks/{track_id}")
async def delete_track_endpoint(track_id: str):
    try:
        deleted = delete_track(track_id)
    except TrackKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except TrackNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete track") from None
    return {"deleted": True, "track_id": track_id, "objects_deleted": deleted}
