<!-- last_verified: 2026-06-18 -->
# Feature: Stem Library

## Purpose
A scoped, per-track explorer over the `tracks/` prefix: see each track's status
and four stems, play any stem inline, download it, or delete the whole track.

## Used By
- UI: `/library` page
- API: `GET /tracks`, `GET /tracks/{track_id}`, `DELETE /tracks/{track_id}`,
  and (reused from the file browser) `GET /files/{key}/preview`, `GET /files/{key}/download`

## Core Functions
- `apps/web/src/components/library/track-library.tsx` — list + delete-confirm dialog
- `apps/web/src/components/library/track-card.tsx` — per-track row, status badge, stem chips, lazy detail fetch
- `apps/web/src/components/library/stem-player.tsx` — inline `<audio>` (preview URL) + download
- `apps/web/src/lib/queries.ts` — `useTracks()`, `useTrack()`, `useDeleteTrack()`
- `services/api/app/runtime/tracks.py` — list / detail / delete handlers
- `services/api/app/service/tracks.py` — grouping + status overlay + scoped delete
- `services/api/app/service/track_grouping.py` — flat-key → per-track grouping

## Inputs
- track_id: string (validated against path-traversal + a strict `[a-z0-9-]` pattern)

## Outputs
- `GET /tracks` → `TrackSummary[]` (newest-first; status overlaid from the job registry)
- `GET /tracks/{id}` → `TrackDetail` (includes `stems[]` with keys + sizes)
- `DELETE /tracks/{id}` → `{deleted, track_id, objects_deleted}`

## Polling
While any track is `pending`/`processing`, `useTracks()` auto-polls every 4s
(`refetchInterval`) so stems appear as separation finishes — no manual refresh.
An expanded card's `useTrack()` polls the same way until that track is `done`.

## Streaming & download (reuse, DRY)
Stem playback uses the file browser's `GET /files/{key}/preview` (inline,
does not bump the download counter); the Download button uses
`GET /files/{key}/download` (attachment disposition, 10-min presigned expiry).

## Scoped delete
`delete_track(track_id)` lists `tracks/<track_id>/` and deletes only those keys,
with a defensive prefix re-check per object. It never performs a broad wipe.

## Edge Cases
- Track still processing → stem rows show a "not ready yet" note; chips show which roles exist
- Failed separation → card shows the captured error
- Invalid track id → 400; unknown / already-deleted track → 404
- B2 unreachable → inline ErrorState with Retry

## UX States
- Empty: "No tracks yet" prompt
- Loading: skeleton rows
- Error: inline ErrorState
- Loaded: track cards with status badge, stem chips, and expandable stem players

## Verification
- Test files: `services/api/tests/test_tracks.py`
- Required cases: grouping from flat keys, done-status overlay, scoped delete
  touches only the track prefix, track-id validation, 404 on empty track
- Quick verify: `pnpm test:api`
- Pass criteria: all pytest green, no ruff violations

## Related Docs
- [Stem Separation](stem-separation.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
