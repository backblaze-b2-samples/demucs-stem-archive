<!-- last_verified: 2026-06-18 -->
# Feature: Stem Separation

## Purpose
Split an archived audio track into four stems (vocals, drums, bass, other)
using **Demucs (htdemucs)** run locally, and upload each stem to Backblaze B2.

## Used By
- Worker: `service/separation.py` (background `ThreadPoolExecutor`)
- Indirectly by API: `POST /tracks` enqueues a job; status surfaces via `GET /tracks`

## Core Functions
- `services/api/app/service/separation.py`
  - `enqueue_separation(track_id, source_name, audio)` — registers a pending job, submits to the worker pool
  - `_run_job(...)` — writes input to a temp file, runs Demucs, uploads stems, updates job state
  - `_run_demucs(input_path, out_dir)` — runs the **subprocess** and returns the output dir
  - `get_job(track_id)` — thread-safe snapshot of job status

## The subprocess invariant
Demucs (and torch) run **only as a subprocess**:

```
python -m demucs -n <DEMUCS_MODEL> [-d <DEMUCS_DEVICE>] --out <tmpdir> <input>
```

The `-d` flag is **conditional**. Demucs has no `auto` device value; its native
default already picks CUDA-if-available-else-CPU. So when `DEMUCS_DEVICE` is the
shipped default `auto`, `_run_demucs` **omits `-d` entirely** and lets Demucs
auto-detect. An explicit value (`cpu`, `cuda`, `mps`, …) is passed through as
`-d <device>`. (Passing `-d auto` literally raises
`RuntimeError: Expected one of cpu, cuda, … device type … : auto`.)

Stems are written by torchaudio's `ta.save()`, which since torchaudio 2.11
routes through **TorchCodec** — hence `torchcodec` is a runtime dependency and
the system `ffmpeg` must be on PATH (TorchCodec encodes through it).

Nothing in this module imports torch or demucs at module top level, so
`from main import app` and pytest collection stay light and torch-free. Tests
mock `_run_demucs` (in `tests/conftest.py`) — the real model never runs in CI.

## Inputs
- track_id: string
- source_name: string (original filename, to preserve extension for the decoder)
- audio: bytes (the uploaded track)

## Outputs
- 4 objects in B2: `tracks/<track_id>/stems/{vocals,drums,bass,other}.wav`
- In-memory job state: `status` (pending → processing → done|failed),
  `stems_done`, `error`

## Statuses
- `pending` — enqueued, not yet started
- `processing` — Demucs subprocess running / stems uploading
- `done` — all 4 stems uploaded
- `failed` — subprocess or upload error (captured in `error`)

## Write amplification
1 original → 4 stems = **5 objects per track**. The dashboard surfaces the
ratio (`objects / originals`) across the whole archive.

## Edge Cases
- Demucs nonzero exit → job marked `failed` with truncated stderr
- Missing expected stem WAV → `failed`
- Worker exception → captured into job state; the worker thread never dies
- First run downloads htdemucs weights (~80 MB) into the torch hub cache
- Temp files always removed in a `finally` block

## Verification
- Test files: `services/api/tests/test_separation.py`
- Required cases: 4 stems uploaded + `done`, failure captured, enqueue registers `pending`,
  `-d` omitted when device is `auto`, `-d <device>` passed for an explicit device
- Quick verify: `pnpm test:api`
- Pass criteria: all pytest green; torch is never imported during tests

## Related Docs
- [Track Ingest](track-ingest.md)
- [Stem Library](stem-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
