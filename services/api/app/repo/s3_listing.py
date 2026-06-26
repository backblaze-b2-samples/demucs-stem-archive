import logging
import time
from datetime import datetime
from typing import TypedDict

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
B2_LIST_PAGE_SIZE = 1000


class B2ListingDeadlineError(RuntimeError):
    """Raised when a paginated B2 listing exceeds its request deadline."""


class S3ObjectSummary(TypedDict):
    key: str
    size: int
    last_modified: datetime


def _object_summary(obj: dict) -> S3ObjectSummary:
    return {
        "key": obj["Key"],
        "size": obj["Size"],
        "last_modified": obj["LastModified"],
    }


def _duration_ms(start: float) -> float:
    return (time.monotonic() - start) * 1000


def list_objects(
    *,
    client,
    bucket: str,
    prefix: str = "",
    max_items: int | None,
    page_size: int = B2_LIST_PAGE_SIZE,
    failure_message: str,
    operation: str,
    deadline_seconds: float | None = None,
) -> list[S3ObjectSummary]:
    """Return typed S3 object summaries, stopping at the requested budget."""
    if max_items is not None and max_items < 1:
        raise ValueError("max_items must be at least 1")
    if page_size < 1 or page_size > B2_LIST_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {B2_LIST_PAGE_SIZE}")

    start = time.monotonic()
    pages = 0
    contents: list[S3ObjectSummary] = []
    kwargs: dict = {"Bucket": bucket, "Prefix": prefix}
    seen_tokens: set[str] = set()
    try:
        while True:
            if (
                deadline_seconds is not None
                and time.monotonic() - start > deadline_seconds
            ):
                logger.warning(
                    "B2 list deadline exceeded: operation=%s pages=%d objects=%d duration_ms=%.2f",
                    operation,
                    pages,
                    len(contents),
                    _duration_ms(start),
                )
                raise B2ListingDeadlineError(
                    f"{failure_message}: listing deadline exceeded"
                )

            remaining = (
                page_size
                if max_items is None
                else min(page_size, max_items - len(contents))
            )
            if remaining <= 0:
                return contents
            kwargs["MaxKeys"] = remaining
            response = client.list_objects_v2(**kwargs)
            pages += 1
            objects = response.get("Contents", [])
            if max_items is not None:
                objects = objects[: max_items - len(contents)]
            contents.extend(_object_summary(obj) for obj in objects)
            if max_items is not None and len(contents) >= max_items:
                return contents
            if not response.get("IsTruncated"):
                if deadline_seconds is not None:
                    logger.info(
                        "B2 list complete: operation=%s pages=%d objects=%d duration_ms=%.2f",
                        operation,
                        pages,
                        len(contents),
                        _duration_ms(start),
                    )
                return contents
            token = response.get("NextContinuationToken")
            if not token:
                raise RuntimeError(
                    f"{failure_message}: missing continuation token"
                )
            if token in seen_tokens:
                raise RuntimeError(
                    f"{failure_message}: repeated continuation token"
                )
            if not objects:
                raise RuntimeError(
                    f"{failure_message}: empty truncated page"
                )
            seen_tokens.add(token)
            kwargs["ContinuationToken"] = token
    except ClientError as e:
        logger.warning(
            "B2 list failed: operation=%s pages=%d objects=%d duration_ms=%.2f",
            operation,
            pages,
            len(contents),
            _duration_ms(start),
        )
        raise RuntimeError(f"{failure_message}: {e}") from e
