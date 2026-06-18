<!-- last_verified: 2026-06-18 -->
# Feature: Track Ingest

## Purpose
Accept an audio track (MP3/WAV/FLAC) from the browser, archive the original to
Backblaze B2, and enqueue local Demucs separation.

## Used By
- UI: `/upload` (Add Track) page, upload form + dropzone
- API: `POST /tracks`

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — orchestrates dropzone + progress + ingest state
- `apps/web/src/components/upload/dropzone.tsx` — audio drag-and-drop (MP3/WAV/FLAC, 200 MB)
- `apps/web/src/lib/api-client.ts` — `ingestTrack()` using XHR for progress events
- `services/api/app/runtime/tracks.py` — `POST /tracks` handler, reads file chunks
- `services/api/app/service/ingest.py` — `process_ingest()`: validates audio, archives original, enqueues separation
- `services/api/app/repo/b2_client.py` — `upload_file()` via boto3 `put_object`

## Inputs
- file: `File` (browser multipart form data)
- content_type: string (audio/mpeg, audio/wav, audio/flac + aliases)

## Outputs
- `IngestResponse`: `{track_id, title, original_key, status}` (`status = "pending"`)
- Side effects: original stored at `tracks/<track_id>/original/<safe_name>`; a
  separation job is enqueued on the background worker

## Flow
- User drops/selects audio in the dropzone (client rejects non-audio + >200 MB)
- XHR sends multipart `POST /tracks` with progress events
- API checks `Content-Length` early, validates content type against the audio allowlist
- API sanitizes the filename, validates extension matches MIME, rejects empty files
- API builds `track_id = <slug>-<uuid4 hex[:8]>`, archives the original to B2
- API enqueues separation (the upload bytes are handed straight to the worker)
- API returns `IngestResponse`; the Library/dashboard refresh to show the new track

## Edge Cases
- Non-audio type → 415
- Extension/MIME mismatch → 415
- Empty file → 400
- File > 200 MB → client-side rejection + 413 if bypassed
- B2 unreachable → 500

## UX States
- Empty: dropzone with audio instructions
- Loading: per-file progress bars
- Error: red status icon, per-file message
- Complete: green checkmark + "separating stems…" toast

## Verification
- Test files: `services/api/tests/test_ingest.py`
- Required cases: track-id format, filename sanitization, extension/type match,
  non-audio rejection, empty rejection, archive + enqueue happy path
- Quick verify: `pnpm test:api`
- Full verify: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest green, no ruff violations

## Related Docs
- [Stem Separation](stem-separation.md)
- [Stem Library](stem-library.md)
- [App Workflows](../app-workflows.md)
