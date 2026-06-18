<!-- last_verified: 2026-06-18 -->
# App Workflows

User journeys inside the application.

## Add a Track (ingest → separate)

- User navigates to `/upload` (Add Track)
- Drops or selects an MP3, WAV, or FLAC (client rejects non-audio and >200 MB)
- Progress bar shows the upload; on success, a toast says "archived — separating stems…"
- Behind the scenes: original archived to `tracks/<id>/original/<name>`, a Demucs
  separation job is enqueued, and the API returns immediately
- See: [Track Ingest](features/track-ingest.md), [Stem Separation](features/stem-separation.md)

## Watch separation & browse the Stem Library

- User navigates to `/library`
- Each track shows a status badge (Queued / Separating… / 4 stems / Failed) and
  four stem chips indicating which roles exist in B2
- While any job is processing, the list **auto-polls** every 4s — stems appear as
  they finish, no manual refresh
- Expand a track to reveal inline `<audio>` players (one per stem) and a Download
  button per stem
- Delete a track → removes the original + all stems under its prefix only (scoped)
- See: [Stem Library](features/stem-library.md)

## View the Dashboard

- User navigates to `/` (home)
- Stats cards: Tracks, Stems, Audio Stored, and **Write Amplification ×**
- Chart: tracks ingested + stems produced per day (last 7 days)
- Recent separations table: last 10 tracks with stem count + status
- See: [Dashboard](features/dashboard.md)

## Browse the whole bucket (generic explorer)

- User navigates to `/files`
- Tree view of every object in the bucket (including `tracks/...`)
- Hover a row for preview / download / delete
- See: [File Browser](features/file-browser.md)
