<!-- last_verified: 2026-06-18 -->
# Demucs Stem Archive

Turn a growing music library into a durable, browsable **stem archive on
[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-demucs-stem-archive)**.
Drop in an MP3, WAV, or FLAC; the original is archived to B2, then
**[Demucs](https://github.com/adefossez/demucs) (htdemucs)** runs *locally* to
split it into four stems — **vocals, drums, bass, other** — and each stem is
written back to B2 alongside the original. A scoped **Stem Library** browses
the archive per track and streams or downloads any stem straight from the
bucket.

This is a sample app for producers, remix engineers, and karaoke-platform
operators who want their separated stems to live in durable object storage,
not on a laptop.

## The teaching point: write amplification

Every source track lands **5 objects** in B2 — 1 original + 4 stems — so a
100-track archive becomes **500+ audio files**. The dashboard surfaces the
amplification ratio (`objects / originals`) and the storage growth that comes
with it. B2 is the storage layer for the whole workflow, reached entirely
through the **S3-compatible API** with a custom user agent and the standard
`B2_*` environment variables.

The model runs on local open-source software — **no second API key**. Your B2
credentials are the only secret, and per-run cost is $0.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, **ffmpeg** (Demucs decodes
MP3/FLAC through it), and a free
**[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-demucs-stem-archive)**.

### Start a new project

```bash
git clone https://github.com/backblaze-b2-samples/demucs-stem-archive.git
cd demucs-stem-archive
```

### Setup

**1. Install frontend dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

> `pip install -r requirements.txt` pulls in **Demucs**, which depends on
> **torch** + **torchaudio** (a large download). The API process itself never
> imports torch — Demucs is invoked only as a subprocess — so the model weight
> is only loaded by the worker. The **first separation** downloads the htdemucs
> weights (~80 MB) into the torch hub cache. CPU works out of the box; if a
> CUDA GPU is present, `DEMUCS_DEVICE=auto` uses it automatically.

**3. Add your B2 credentials**

```bash
cp .env.example .env
```

Open `.env` and fill it in. Head to the
[Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-demucs-stem-archive)
and:

1. **Create a bucket** → its unique name goes in `B2_BUCKET_NAME`. The bucket's
   region (e.g. `us-west-004`) goes in `B2_REGION`; the S3 endpoint is derived
   as `https://s3.<B2_REGION>.backblazeb2.com`.
2. **Create an application key** with `Read and Write` permission:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(only shown once)*

| Variable | Meaning |
|----------|---------|
| `B2_APPLICATION_KEY_ID` | Application key ID |
| `B2_APPLICATION_KEY` | Application key secret |
| `B2_BUCKET_NAME` | Target bucket name |
| `B2_REGION` | Bucket region, e.g. `us-west-004` (used to build the S3 endpoint) |
| `B2_PUBLIC_URL_BASE` | Optional public base URL for objects (leave blank for private buckets) |

> Want a walkthrough? See the docs for
> [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-demucs-stem-archive)
> and [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-demucs-stem-archive).

**4. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Add a track and watch
the Library auto-update as separation completes.

`pnpm dev` runs `pnpm doctor` first — a preflight check that catches the common
setup gotchas (wrong Node/Python version, missing venv, missing or placeholder
`.env`, ports in use). Run it standalone any time with `pnpm doctor`.

## How it works

```
Add Track (/upload)
  → POST /tracks (multipart)
  → original archived to  tracks/<track_id>/original/<name>
  → separation job enqueued (background thread)
  → `python -m demucs` subprocess produces 4 WAVs
  → each stem uploaded to  tracks/<track_id>/stems/<role>.wav
  → Stem Library (/library) auto-polls and shows stems as they land
```

Key layout in B2:

```
tracks/<track_id>/original/<safe_filename>
tracks/<track_id>/stems/vocals.wav
tracks/<track_id>/stems/drums.wav
tracks/<track_id>/stems/bass.wav
tracks/<track_id>/stems/other.wav
```

`track_id = <slug-of-filename>-<uuid4 hex[:8]>` — human-browsable and
collision-safe.

## Core Features

- [Track Ingest](docs/features/track-ingest.md) — drop MP3/WAV/FLAC; original archived to B2, separation triggered
- [Stem Separation](docs/features/stem-separation.md) — local Demucs subprocess produces 4 stems, status tracked
- [Stem Library](docs/features/stem-library.md) — per-track scoped browse, inline stem playback, download, scoped delete
- [Dashboard](docs/features/dashboard.md) — write-amplification ratio, storage growth, recent separations
- [File Browser](docs/features/file-browser.md) — generic full-bucket browse/preview/download/delete (kept from the starter)
- [Design System](docs/design-system.md) — tokens, primitives, loader, error/empty states. Live preview at `/design`.

Plus: inline error handling, single-source `.env` config validated at startup,
a centralized TanStack Query data layer, structural tests, structured JSON
logging, a `/health` B2-connectivity endpoint, and a Prometheus-format
`/metrics` endpoint.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, retry, polling for every fetch
- Python 3.11+, FastAPI, boto3, Pydantic v2
- Demucs (htdemucs) — local, open-source stem separation, run as a subprocess
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build + typecheck frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests (Demucs subprocess is mocked — torch never runs) |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @demucs-stem-archive/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (ingest, separation, library, dashboard, file browser) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search,
audits, stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)
