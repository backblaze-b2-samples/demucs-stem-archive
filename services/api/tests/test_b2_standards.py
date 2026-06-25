from pathlib import Path

import pytest

from app.config.settings import Settings
from app.repo import b2_client

STANDARD_B2_ENV = (
    "B2_APPLICATION_KEY_ID",
    "B2_APPLICATION_KEY",
    "B2_BUCKET_NAME",
    "B2_REGION",
    "B2_PUBLIC_URL_BASE",
)


def _clear_b2_env(monkeypatch):
    for key in STANDARD_B2_ENV:
        monkeypatch.delenv(key, raising=False)


def _write_env(tmp_path, lines: list[str]):
    env_file = tmp_path / ".env"
    env_file.write_text("\n".join(lines))
    return env_file


def test_env_example_declares_standard_b2_names_only():
    repo_root = Path(__file__).resolve().parents[3]
    env_file = repo_root / ".env.example"

    b2_keys = [
        line.split("=", 1)[0]
        for line in env_file.read_text().splitlines()
        if line.startswith("B2_")
    ]

    assert b2_keys == list(STANDARD_B2_ENV)


def test_settings_parse_standard_b2_env_and_derive_endpoint(
    monkeypatch, tmp_path
):
    _clear_b2_env(monkeypatch)
    env_file = _write_env(
        tmp_path,
        [
            "B2_REGION=aa-bbbb-001",
            "B2_APPLICATION_KEY_ID=key-id",
            "B2_APPLICATION_KEY=application-key",
            "B2_BUCKET_NAME=stem-archive",
            "B2_PUBLIC_URL_BASE=https://cdn.example/stems",
        ],
    )

    settings = Settings(_env_file=env_file)

    assert settings.b2_bucket_name == "stem-archive"
    assert settings.b2_application_key_id == "key-id"
    assert settings.b2_public_url_base == "https://cdn.example/stems"
    assert settings.s3_endpoint == "https://s3.aa-bbbb-001.backblazeb2.com"


@pytest.mark.parametrize(
    "region",
    [
        "attacker.example/steal",
        "aa-bbbb-001#x",
    ],
)
def test_b2_region_rejects_url_metacharacters(
    region, monkeypatch, tmp_path
):
    _clear_b2_env(monkeypatch)
    env_file = _write_env(
        tmp_path,
        [
            f"B2_REGION={region}",
            "B2_APPLICATION_KEY_ID=key-id",
            "B2_APPLICATION_KEY=application-key",
            "B2_BUCKET_NAME=stem-archive",
        ],
    )
    settings = Settings(_env_file=env_file)

    with pytest.raises(ValueError, match="B2_REGION"):
        _ = settings.s3_endpoint


def test_invalid_b2_region_blocks_boto3_client_creation(
    monkeypatch, tmp_path
):
    _clear_b2_env(monkeypatch)
    env_file = _write_env(
        tmp_path,
        [
            "B2_REGION=attacker.example/steal",
            "B2_APPLICATION_KEY_ID=key-id",
            "B2_APPLICATION_KEY=application-key",
            "B2_BUCKET_NAME=stem-archive",
        ],
    )
    settings = Settings(_env_file=env_file)

    b2_client.get_s3_client.cache_clear()
    monkeypatch.setattr(b2_client, "settings", settings)
    monkeypatch.setattr(
        b2_client.boto3,
        "client",
        lambda *_, **__: pytest.fail("boto3 client should not be created"),
    )

    with pytest.raises(ValueError, match="B2_REGION"):
        b2_client.get_s3_client()

    b2_client.get_s3_client.cache_clear()


def test_missing_b2_region_blocks_boto3_client_creation(
    monkeypatch, tmp_path
):
    _clear_b2_env(monkeypatch)
    env_file = _write_env(
        tmp_path,
        [
            "B2_APPLICATION_KEY_ID=key-id",
            "B2_APPLICATION_KEY=application-key",
            "B2_BUCKET_NAME=stem-archive",
        ],
    )
    settings = Settings(_env_file=env_file)

    b2_client.get_s3_client.cache_clear()
    monkeypatch.setattr(b2_client, "settings", settings)
    monkeypatch.setattr(
        b2_client.boto3,
        "client",
        lambda *_, **__: pytest.fail("boto3 client should not be created"),
    )

    with pytest.raises(RuntimeError, match="B2_REGION"):
        b2_client.get_s3_client()

    b2_client.get_s3_client.cache_clear()


def test_b2_public_url_base_trailing_slash_is_normalized(
    monkeypatch, tmp_path
):
    _clear_b2_env(monkeypatch)
    env_file = _write_env(
        tmp_path,
        [
            "B2_REGION=aa-bbbb-001",
            "B2_APPLICATION_KEY_ID=key-id",
            "B2_APPLICATION_KEY=application-key",
            "B2_BUCKET_NAME=stem-archive",
            "B2_PUBLIC_URL_BASE=https://cdn.example/stems/",
        ],
    )
    settings = Settings(_env_file=env_file)

    monkeypatch.setattr(b2_client, "settings", settings)

    assert (
        b2_client._public_url("tracks/demo song.mp3")
        == "https://cdn.example/stems/tracks/demo%20song.mp3"
    )


def test_s3_client_uses_standard_user_agent_and_region(
    monkeypatch, tmp_path
):
    _clear_b2_env(monkeypatch)
    env_file = _write_env(
        tmp_path,
        [
            "B2_REGION=aa-bbbb-001",
            "B2_APPLICATION_KEY_ID=key-id",
            "B2_APPLICATION_KEY=application-key",
            "B2_BUCKET_NAME=stem-archive",
        ],
    )
    settings = Settings(_env_file=env_file)
    captured = {}

    def fake_client(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return object()

    b2_client.get_s3_client.cache_clear()
    monkeypatch.setattr(b2_client, "settings", settings)
    monkeypatch.setattr(b2_client.boto3, "client", fake_client)

    b2_client.get_s3_client()

    assert captured["args"] == ("s3",)
    assert (
        captured["kwargs"]["endpoint_url"]
        == "https://s3.aa-bbbb-001.backblazeb2.com"
    )
    assert captured["kwargs"]["region_name"] == "aa-bbbb-001"
    assert captured["kwargs"]["config"].user_agent_extra == (
        "b2ai-demucs-stem-archive (backblaze-b2-samples)"
    )

    b2_client.get_s3_client.cache_clear()
