from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) ---
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    # Region drives the default S3 endpoint. Never hardcode a region in
    # source — it always comes from the environment.
    b2_region: str = ""
    # Optional explicit endpoint override. When empty, the S3 client builds
    # `https://s3.{b2_region}.backblazeb2.com` from b2_region.
    b2_endpoint: str = ""
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits — bumped to 200 MB for lossless WAV/FLAC originals.
    max_file_size: int = 200 * 1024 * 1024  # 200MB

    # --- Demucs stem separation ---
    # Pre-trained Hybrid Transformer model. First run downloads the
    # weights (~80MB) into the torch hub cache.
    demucs_model: str = "htdemucs"
    # auto | cpu | cuda — passed through to `python -m demucs -d <device>`.
    # "auto" lets demucs pick CUDA when available, else CPU.
    demucs_device: str = "auto"
    # All archived tracks live under this prefix in the bucket.
    tracks_prefix: str = "tracks/"

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def s3_endpoint(self) -> str:
        """Resolved S3 endpoint URL. Explicit override wins; otherwise the
        URL is derived from the region so no endpoint/region drift is
        possible."""
        if self.b2_endpoint:
            return self.b2_endpoint
        return f"https://s3.{self.b2_region}.backblazeb2.com"


settings = Settings()
