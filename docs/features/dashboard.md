<!-- last_verified: 2026-06-18 -->
# Feature: Dashboard

## Purpose
An at-a-glance view of the stem archive: how many tracks and stems exist, how
much audio is stored, and the **write-amplification ratio** (objects per
original).

## Used By
- UI: `/` (dashboard home)
- API: `GET /tracks/stats`, `GET /tracks/stats/activity`, `GET /tracks`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — Tracks / Stems / Audio Stored / Write Amplification ×
- `apps/web/src/components/dashboard/archive-chart.tsx` — tracks ingested + stems produced per day
- `apps/web/src/components/dashboard/recent-separations-table.tsx` — last 10 tracks with status
- `apps/web/src/lib/queries.ts` — `useArchiveStats()`, `useArchiveActivity()`, `useTracks()`
- `services/api/app/runtime/tracks.py` — stats + activity handlers
- `services/api/app/service/tracks.py` — `get_archive_stats()`, `get_activity()`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /tracks/stats` → `ArchiveStats` (track_count, stem_count, object_count,
  total_size_*, amplification_ratio, separations_today, processing_count, failed_count)
- `GET /tracks/stats/activity?days=7` → `DailyActivity[]` (tracks + stems per day)
- `GET /tracks` (sliced to 10) → recent separations table

## Flow
- Page loads → parallel queries for archive stats, activity, and recent tracks
- Stats cards show tracks, stems, total audio stored, and the amplification ratio
- Chart shows daily tracks ingested + stems produced (last 7 days)
- Recent separations table shows the last 10 tracks with stem count + status
- While any separation is in flight, stats + tracks auto-poll so the numbers move

## Edge Cases
- API unavailable → inline ErrorState (cards don't render misleading zeros)
- Empty archive → empty chart + table states
- Large archive → stats endpoint paginates objects via `list_objects_v2`

## UX States
- Loading: skeletons for cards, chart, table
- Empty: "No tracks yet" messages
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_tracks.py`
- Required cases: amplification math (10 objects / 2 originals = 5.0), activity counts
- Quick verify: `pnpm test:api`
- Pass criteria: all pytest green, no ruff violations

## Related Docs
- [Stem Library](stem-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
