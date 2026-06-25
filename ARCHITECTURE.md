<!-- last_verified: 2026-06-18 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with archive metrics (tracks, stems, storage, write-amplification ×)
  - Add Track surface (audio dropzone + ingest progress)
  - Stem Library (`/library`) — scoped per-track browse, inline stem playback, download, scoped delete
  - File Browser (`/files`) — generic full-bucket explorer (kept from the starter)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - `POST /tracks` ingest, `GET /tracks` library, stats + activity, `GET /tracks/{id}`, scoped `DELETE /tracks/{id}`
  - Generic `/files` bucket-explorer router (list/get/download/preview/delete)
  - **Separation worker** — runs Demucs as a subprocess and uploads stems to B2
  - **In-memory job registry** — thread-safe per-track separation status
  - B2 S3 integration via boto3 (confined to `repo/`)
  - Health check, structured JSON logging, Prometheus metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` → `config` → `repo` → `service` → `runtime`
2. No backward imports (e.g. service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, Track*, ArchiveStats, ...)
    config/                Settings loaded from environment
    repo/                  B2 S3 client (data access layer)
    service/
      ingest.py            Audio validation + archive original + enqueue separation
      separation.py        Demucs subprocess worker + in-memory job registry
      track_grouping.py    Pure key/metadata grouping of flat `tracks/` keys
      tracks.py            Library listing, archive stats, scoped delete
      files.py             Generic bucket-explorer business logic (kept)
    runtime/               FastAPI route handlers (tracks, files, health, metrics)
  tests/                   pytest tests (structural + integration)
```

## The Demucs subprocess trust boundary

Demucs (and therefore **torch**) is **never imported into the API process**.
`service/separation.py` runs the model strictly as a child process:

```
python -m demucs -n <model> -d <device> --out <tmpdir> <input>
```

This keeps the API importable and the test suite light — `from main import app`
and pytest collection work with only the light deps installed (no torch). The
worker writes the input to a temp file, runs the subprocess, collects the four
output WAVs, uploads each to B2, and updates the in-memory job registry. Temp
files are always cleaned up in a `finally` block.

A `ThreadPoolExecutor(max_workers=1)` owns the jobs so the ingest request
returns immediately and runs queue behind each other (one CPU/GPU-heavy run at
a time).

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole durable store
  - Key layout:
    ```
    tracks/<track_id>/original/<safe_filename>
    tracks/<track_id>/stems/vocals.wav
    tracks/<track_id>/stems/drums.wav
    tracks/<track_id>/stems/bass.wav
    tracks/<track_id>/stems/other.wav
    ```
  - Listing / grouping / stats via `list_objects_v2`; metadata via `head_object`
- **In-memory job registry** — transient separation status only. Durable
  artifacts always live in B2, so a restart loses only live status, never stems.

## B2 surface (S3-compatible API only)

| Op | S3 call | Where |
|----|---------|-------|
| Archive original + 4 stems | `put_object` | repo `upload_file` |
| Library grouping, explorer, stats | `list_objects_v2` (paginated) | repo `list_files` / `get_upload_stats` |
| Asset metadata | `head_object` | repo `get_file_metadata` |
| Stream / download | `generate_presigned_url` (GET, attachment, 10-min) | repo `get_presigned_url` |
| Re-separate fetch | `get_object` | repo `download_file` |
| Delete asset / scoped track delete | `delete_object` | repo `delete_file` |
| Health | `head_bucket` | repo `check_connectivity` |

- No b2-native API anywhere. boto3 confined to `repo/` (enforced by `test_boto3_only_in_repo`).
- Custom user-agent `user_agent_extra="b2ai-demucs-stem-archive (backblaze-b2-samples)"` on the S3 client.
- The S3 endpoint is built from `B2_REGION` (`https://s3.{region}.backblazeb2.com`).
  No region string or alternate endpoint env var is hardcoded in source.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend → API** — CORS-restricted to configured origins
- **API → B2** — authenticated via application keys, signature v4
- **API → Demucs subprocess** — fixed argv, no shell; only app-controlled temp paths
- **Client → B2** — presigned URLs for stream/download (10-min expiry, forced attachment)

## Data Flows

- **Ingest**: Browser → `POST /tracks` (multipart) → API validates audio →
  archives original to B2 → enqueues separation → returns `{track_id, status: pending}`
- **Separate**: worker thread → `python -m demucs` subprocess → 4 WAVs → upload
  each to `tracks/<id>/stems/<role>.wav` → job status → `done`
- **Library**: Browser → `GET /tracks` → service groups flat keys + overlays job
  status; while any job is processing the UI auto-polls (`refetchInterval`)
- **Stream/Download**: Browser → `/files/{key}/preview` (inline) or
  `/files/{key}/download` (attachment) → presigned URL → browser plays/downloads
- **Delete track**: Browser → `DELETE /tracks/{id}` → service deletes every key
  under `tracks/<id>/` only (scoped, never a broad wipe)

## Deployment

This sample is **local-first**: the Demucs worker is CPU/GPU-bound and meant to
run on the operator's own machine, next to the model weights. `pnpm dev` runs
both services via `concurrently` (web on `localhost:3000`, API on
`localhost:8000`). Durable artifacts live in B2, so the worker host is
stateless beyond the in-memory job registry.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, ingest count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Ingest handler: `services/api/app/runtime/tracks.py`
- Separation worker (subprocess + job registry): `services/api/app/service/separation.py`
- Track grouping logic: `services/api/app/service/track_grouping.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`files.py`, `tracks.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- TanStack Query hooks: `apps/web/src/lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
