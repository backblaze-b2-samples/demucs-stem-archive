from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    """Lightweight per-object detail for the full-bucket explorer.

    The audio workflow stores write-amplification info from object sizes
    alone (no audio probing), so this carries only the core, type-agnostic
    fields: identity, size, mime, extension, checksums, timestamp.
    """

    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
