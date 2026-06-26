from datetime import UTC, datetime, timedelta

import pytest

from app.repo import b2_client


def _object(
    key: str, age_minutes: int, last_modified: datetime | None = None
) -> dict:
    return {
        "Key": key,
        "Size": 10,
        "LastModified": last_modified
        or datetime.now(UTC) - timedelta(minutes=age_minutes),
    }


def test_list_files_paginates_until_listing_complete_within_limit(monkeypatch):
    class FakeS3Client:
        def __init__(self):
            self.calls: list[dict] = []

        def list_objects_v2(self, **kwargs):
            self.calls.append(kwargs.copy())
            if len(self.calls) == 1:
                return {
                    "IsTruncated": True,
                    "NextContinuationToken": "page-2",
                    "Contents": [
                        _object("tracks/a/original/a.wav", age_minutes=30),
                    ],
                }
            return {
                "IsTruncated": False,
                "Contents": [
                    _object("tracks/b/original/b.wav", age_minutes=10),
                    _object("tracks/c/original/c.wav", age_minutes=20),
                ],
            }

    fake_client = FakeS3Client()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "test-bucket")

    files = b2_client.list_files(prefix="tracks/", max_keys=3)

    assert [f.key for f in files] == [
        "tracks/b/original/b.wav",
        "tracks/c/original/c.wav",
        "tracks/a/original/a.wav",
    ]
    assert fake_client.calls == [
        {
            "Bucket": "test-bucket",
            "Prefix": "tracks/",
            "MaxKeys": 3,
        },
        {
            "Bucket": "test-bucket",
            "Prefix": "tracks/",
            "MaxKeys": 2,
            "ContinuationToken": "page-2",
        },
    ]


def test_list_files_respects_total_max_keys_across_pages(monkeypatch):
    class FakeS3Client:
        def __init__(self):
            self.calls: list[dict] = []

        def list_objects_v2(self, **kwargs):
            self.calls.append(kwargs.copy())
            if len(self.calls) == 1:
                return {
                    "IsTruncated": True,
                    "NextContinuationToken": "page-2",
                    "Contents": [
                        _object("tracks/a/original/a.wav", age_minutes=30),
                    ],
                }
            return {
                "IsTruncated": True,
                "NextContinuationToken": "page-3",
                "Contents": [
                    _object("tracks/b/original/b.wav", age_minutes=10),
                    _object("tracks/c/original/c.wav", age_minutes=20),
                ],
            }

    fake_client = FakeS3Client()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "test-bucket")

    files = b2_client.list_files(prefix="tracks/", max_keys=2)

    assert [f.key for f in files] == [
        "tracks/b/original/b.wav",
        "tracks/a/original/a.wav",
    ]
    assert fake_client.calls == [
        {
            "Bucket": "test-bucket",
            "Prefix": "tracks/",
            "MaxKeys": 2,
        },
        {
            "Bucket": "test-bucket",
            "Prefix": "tracks/",
            "MaxKeys": 1,
            "ContinuationToken": "page-2",
        },
    ]


@pytest.mark.asyncio
async def test_files_endpoint_limit_uses_single_bounded_b2_page(
    client, monkeypatch
):
    class FakeS3Client:
        def __init__(self):
            self.calls: list[dict] = []

        def list_objects_v2(self, **kwargs):
            self.calls.append(kwargs.copy())
            return {
                "IsTruncated": True,
                "NextContinuationToken": "page-2",
                "Contents": [
                    _object("uploads/one.txt", age_minutes=0),
                    *[
                        _object(f"uploads/file-{index}.txt", age_minutes=10)
                        for index in range(999)
                    ],
                ],
            }

    fake_client = FakeS3Client()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "test-bucket")

    response = await client.get("/files?limit=1")

    assert response.status_code == 200
    assert [file["key"] for file in response.json()] == ["uploads/one.txt"]
    assert fake_client.calls == [
        {
            "Bucket": "test-bucket",
            "Prefix": "",
            "MaxKeys": 1000,
        },
    ]


def test_list_files_rejects_invalid_max_keys():
    with pytest.raises(ValueError, match="max_keys must be at least 1"):
        b2_client.list_files(max_keys=0)


def test_get_upload_stats_paginates_all_pages(monkeypatch):
    fixed_now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)

    class FixedDateTime:
        @staticmethod
        def now(_tz):
            return fixed_now

    class FakeS3Client:
        def __init__(self):
            self.calls: list[dict] = []

        def list_objects_v2(self, **kwargs):
            self.calls.append(kwargs.copy())
            if len(self.calls) == 1:
                return {
                    "IsTruncated": True,
                    "NextContinuationToken": "page-2",
                    "Contents": [
                        _object(
                            "tracks/a/original/a.wav",
                            age_minutes=0,
                            last_modified=fixed_now,
                        ),
                    ],
                }
            return {
                "IsTruncated": False,
                "Contents": [
                    _object(
                        "tracks/b/stems/vocals.wav",
                        age_minutes=0,
                        last_modified=fixed_now,
                    ),
                    _object(
                        "tracks/b/stems/drums.wav",
                        age_minutes=0,
                        last_modified=fixed_now,
                    ),
                ],
            }

    fake_client = FakeS3Client()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(b2_client, "datetime", FixedDateTime)
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "test-bucket")

    stats = b2_client.get_upload_stats()

    assert stats["total_files"] == 3
    assert stats["total_size_bytes"] == 30
    assert stats["uploads_today"] == 3
    assert fake_client.calls == [
        {
            "Bucket": "test-bucket",
            "Prefix": "",
            "MaxKeys": 1000,
        },
        {
            "Bucket": "test-bucket",
            "Prefix": "",
            "MaxKeys": 1000,
            "ContinuationToken": "page-2",
        },
    ]
