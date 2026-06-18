<!-- last_verified: 2026-05-01 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
packages/shared/   Shared TypeScript types
docs/              System of record (features, workflows, security, reliability)
```

## 2. What This App Is

`demucs-stem-archive` archives audio tracks to Backblaze B2 and splits each one
into four stems (vocals, drums, bass, other) with **Demucs**, run locally. Every
track becomes 5 objects in B2 (1 original + 4 stems) — the "write amplification"
teaching point.

**Surfaces**
- **Add Track** (`/upload`) — audio dropzone; `POST /tracks` archives the
  original and enqueues separation. (The starter's generic Upload, specialized
  to audio ingest.)
- **Stem Library** (`/library`) — scoped per-track explorer: status, the four
  stem chips, inline `<audio>` playback, download, and scoped track delete.
  Auto-polls (`refetchInterval`) while any job is processing.
- **Dashboard** (`/`) — archive metrics: tracks, stems, audio stored, and the
  write-amplification ratio; a separation-activity chart; recent separations.
- **File Browser** (`/files`) — the generic full-bucket explorer, **kept from
  the starter**. The Library reuses its `/files/{key}/preview` and
  `/files/{key}/download` endpoints for streaming and download (DRY).
- **Settings** (`/settings`) and the **Design System** reference (`/design`).

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives),
  design tokens in `apps/web/src/app/globals.css`, and `/design`. Never edit
  generated `components/ui/` files directly; restyle through tokens.
- **File Explorer.** `/files` route + `apps/web/src/components/files/` +
  `runtime/files.py`. Its Files sidebar entry stays.

**Adapt with the use case**
- **Dashboard.** Already adapted to archive metrics. Any further change must flow
  through the same `runtime -> service -> repo` layering and be exposed via
  TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare
  `useEffect + fetch`. Update `docs/features/dashboard.md` in the same PR (§9).

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers — except the in-memory separation job
  registry in `service/separation.py`, which is explicitly thread-safe (guarded
  by a `Lock`) and transient (durable artifacts live in B2)
- **Demucs only via subprocess.** Run Demucs strictly as
  `python -m demucs ...` from `service/separation.py`. **Never** `import torch`
  or `import demucs` in-process — that would break `from main import app` and
  pytest collection, which must work with only the light deps installed. Tests
  mock `_run_demucs` (see `tests/conftest.py`); torch never runs in tests.

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
