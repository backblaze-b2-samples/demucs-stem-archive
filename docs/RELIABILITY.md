<!-- last_verified: 2026-03-06 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- Track/file listing returns an empty list (not an error) when B2 has no objects
- A failed Demucs run is captured into job state (status `failed` + message) and
  never crashes the worker thread or the API
- Frontend shows skeleton states while loading, inline error states on failure

## Separation Job State

- Separation status (pending/processing/done/failed) lives in an **in-memory,
  thread-safe registry** in `service/separation.py` — it is transient
- This is acceptable because the **durable artifacts always live in B2**: on a
  restart, in-flight jobs lose only their live status, never their stems. The
  Library reconstructs status from the objects present in the bucket (all 4
  stems present ⇒ `done`)
- A single-worker `ThreadPoolExecutor` runs one separation at a time, so a
  CPU/GPU-heavy run never thrashes the host

## Deployment

- **Local-first.** The Demucs worker is CPU/GPU-bound and meant to run on the
  operator's machine. `pnpm dev` runs web + API via `concurrently`.
- Environment-specific configuration via env vars (no config files)
