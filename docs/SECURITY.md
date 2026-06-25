<!-- last_verified: 2026-06-25 -->
# Security

Security principles and implementation for the demucs-stem-archive.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` +
  `B2_APPLICATION_KEY`, signature v4, derived endpoint from `B2_REGION`, and
  `user_agent_extra="b2ai-demucs-stem-archive (backblaze-b2-samples)"`
- **API -> Demucs subprocess**: fixed argv, no shell; only app-controlled temp paths are passed
- **Client -> B2**: Presigned URLs for stream/download (10-min expiry, `Content-Disposition: attachment`)

## Ingest Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against the audio allowlist (MP3/WAV/FLAC)
- Chunked streaming with size enforcement (200 MB default)
- Empty file rejection

## Subprocess Handling

- Demucs is invoked with a fixed argument vector and **no shell** — there is no
  string interpolation into a shell command, so a filename can't inject args
- Uploaded bytes are written to a per-job temp directory; the input path is
  app-generated, not user-controlled
- Temp directories are always removed in a `finally` block, even on failure

## Key / Track-ID Validation

- Empty keys rejected; path-traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- `track_id` must additionally match a strict `[a-z0-9-]` pattern before any
  B2 operation (`service/tracks.py::validate_track_id`)
- Track delete is **scoped**: only keys under `tracks/<track_id>/` are deleted,
  with a per-object prefix re-check — never a broad wipe

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)
- Inline stem playback uses the preview endpoint (also presigned, short-lived)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
