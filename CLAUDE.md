# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**YouTube 라이브스트리밍 스케쥴러** — A local web app for scheduling YouTube livestreams and automating OBS control via WebSocket. Single-user, personal tool running on localhost.

**Vision**: Three sub-projects (1) Schedule-based streaming ← **this repo**, (2) Video collection→edit→upload pipeline, (3) YouTube analytics dashboard.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, APScheduler, obs-websocket-py v1.6+
- **Frontend**: React 18, Vite 5, TypeScript 5.5+
- **Database**: SQLite (local, not committed)
- **External APIs**: YouTube Data API v3 (OAuth 2.0), OBS WebSocket v5
- **Testing**: pytest + pytest-asyncio (backend), Vitest (frontend)

## Project Structure

```
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                 # FastAPI app, lifespan, routers
│   │   ├── config.py               # Settings (DB path, OBS addr, ports)
│   │   ├── db.py                   # SQLAlchemy engine/session
│   │   ├── models.py               # ORM: OAuthToken, Scene, Broadcast, Schedule, SequenceItem, RunLog
│   │   ├── schemas.py              # Pydantic input/output schemas
│   │   ├── crud.py                 # DB helpers (log_run, set_*_status)
│   │   ├── clients/
│   │   │   ├── obs_client.py       # OBSClient wrapping obs-websocket v5
│   │   │   └── youtube_client.py   # YouTubeClient wrapping google-api-python-client
│   │   ├── scheduler/
│   │   │   ├── engine.py           # ScheduleEngine (APScheduler wrapper)
│   │   │   ├── steps.py            # Execution step functions (go_live, switch_to_item, go_complete)
│   │   │   └── recurrence.py       # RRULE next occurrence calculation
│   │   └── routers/
│   │       ├── auth.py             # POST /auth/youtube*, load_credentials()
│   │       ├── broadcasts.py       # CRUD + POST /broadcasts/{id}/youtube
│   │       ├── scenes.py           # CRUD + POST /scenes/sync (OBS sync)
│   │       ├── schedules.py        # CRUD + ScheduleEngine.register/cancel
│   │       └── status.py           # GET /status (WebSocket ready)
│   └── tests/
│       ├── conftest.py             # In-memory DB fixture, mocking
│       ├── test_*.py               # Unit + integration tests (TDD)

├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── types.ts                # TypeScript interfaces (Broadcast, Scene, Schedule, Status)
│   │   ├── api/client.ts           # Fetch wrapper (http://localhost:8000)
│   │   ├── pages/                  # Dashboard, Broadcasts, Schedules, Scenes, Settings
│   │   └── components/
│   └── tests/

└── docs/superpowers/
    ├── specs/2026-06-28-youtube-livestream-scheduler-design.md
    └── plans/2026-06-28-youtube-livestream-scheduler.md
```

## Build & Run

### Backend

**Python**: Use Homebrew Python 3.11+ at `/opt/homebrew/bin/python3.11` (system Python is 3.9.6 — too old).

```bash
cd backend
/opt/homebrew/bin/python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

> Existing `.venv` uses Python 3.14 (also fine — all deps install cleanly).

Start server:
```bash
# Dev with auto-reload — bind to 127.0.0.1 explicitly (OrbStack occupies localhost:8000 via IPv6)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Or via Python directly
python -c "from app.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)"
```

> **OrbStack conflict**: `curl localhost:8000` hits OrbStack (IPv6). Always use `127.0.0.1:8000` or `--host 127.0.0.1`.
> OBS `ConnectionRefusedError` at startup is expected when OBS is not running — server starts fine.

Run tests:
```bash
pytest tests/ -v
pytest tests/test_models.py::test_create_broadcast_and_schedule -v  # Single test
pytest -k "test_go_live" -v                                         # By pattern
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # Vite dev server on :5173
npm run build  # Production build
npm test       # Vitest
```

## Architecture & Key Decisions

### Execution Flow

1. **Schedule Registration** (DB startup or API POST /schedules)
   - APScheduler registers jobs for start_at, end_at, and mid-sequence transitions
   - RRULE used for repeating schedules (RFC 5545 format)

2. **Broadcast Lifecycle**
   - **T-0 (start_at)**: `go_live()` → YouTube transition to "live" → inject stream key to OBS → start_stream() → switch to first scene
   - **T-middle**: Sequence items auto-switch scenes after duration_seconds
   - **T-end**: `go_complete()` → stop_stream() → YouTube transition to "complete"

3. **Error Recovery**
   - Failed steps set broadcast status=error, log to run_log, re-raise
   - OBS/YouTube clients wrapped for mocking in tests

### Data Model Highlights

- **Broadcast**: YouTube event (title, privacy, youtube_broadcast_id, youtube_stream_key, status)
- **Schedule**: Execution time + recurrence (RRULE string) + reference to Broadcast
- **SequenceItem**: Ordered scenes within a schedule (order_index, duration_seconds)
- **RunLog**: Audit trail (timestamp, event, detail)
- All times stored as UTC; frontend converts to local

### External Integrations

| Service | Auth | Config | Notes |
|---------|------|--------|-------|
| **YouTube Data API v3** | OAuth 2.0 (refresh_token in DB) | `.env CLIENT_SECRET_PATH` (`.gitignore`) | liveBroadcasts/liveStreams CRUD, pre-create to save quota |
| **OBS WebSocket v5** | Optional password | `.env OBS_HOST`, `.env OBS_PORT`, `.env OBS_PASSWORD` | SetCurrentProgramScene, StartStream, StopStream, SetStreamServiceSettings |

### Constraints

- **localhost only** — no external access, no deployment
- **Single user** — no auth/permissions beyond OAuth token for YouTube
- **TDD mandatory** — failing test → min implementation → passing test → commit
- **External APIs mocked in tests** — `OBSClient(req_factory=MagicMock)`, mock YouTube resource
- **No secrets in git** — `.gitignore` covers `client_secret_*.json`, `*token*.json`, `.env*`, `*.db`

## Configuration

Environment variables (`.env` file, not committed):
```bash
DB_PATH=backend/scheduler.db          # SQLite file
OBS_HOST=localhost
OBS_PORT=4455
OBS_PASSWORD=<optional>
PORT=8000
CLIENT_SECRET_PATH=path/to/client_secret_*.json  # Google OAuth
```

Frontend always assumes backend on http://localhost:8000.

## Testing Strategy

**Backend (pytest)**:
- Mock OBSClient and YouTubeClient (never hit real services)
- In-memory SQLite for API tests
- Test each scheduler step function
- RRULE next_occurrence calculation
- conftest.py provides `db` fixture

**Frontend (Vitest)**:
- Mock global.fetch for API client
- Component unit tests
- No E2E in automated tests (manual with real OBS + test YouTube account)

Run all:
```bash
cd backend && pytest tests/ -v
cd frontend && npm test
```

## Key Files to Know

- **app/scheduler/engine.py** — Core APScheduler wrapper; `ScheduleEngine.register(schedule_id)` does all job setup
- **app/scheduler/steps.py** — `go_live()`, `switch_to_item()`, `go_complete()` orchestrate YouTube + OBS
- **app/clients/obs_client.py** & **youtube_client.py** — API wrappers; dependency-inject req/resource for testing
- **app/routers/auth.py** — OAuth flow, `load_credentials()` helper
- **frontend/src/api/client.ts** — Centralized fetch wrapper; add methods here for new endpoints

## OAuth Setup (First Time)

1. Get Google OAuth credentials from console.cloud.google.com
2. Create `client_secret_95002751475-*.apps.googleusercontent.com.json`
3. Set `CLIENT_SECRET_PATH` env var (or use default in config.py)
4. Backend lifespan calls `_build_youtube_client()` from oauth_token table (starts None until user does `/auth/youtube`)

## Common Tasks

### Add a new API endpoint
1. Add Pydantic schema in `app/schemas.py`
2. Add route in `app/routers/*.py`, inject `db=Depends(get_db)` + other deps
3. Add test in `backend/tests/test_api_*.py`, override dependencies
4. Frontend: add method in `src/api/client.ts`, type via `src/types.ts`

### Add a new DB table
1. Add ORM model in `app/models.py`
2. Add Pydantic schema for I/O
3. Write failing test in `tests/test_models.py`, then implement
4. Commit once tests pass

### Modify execution flow (go_live, sequence, go_complete)
1. Edit `app/scheduler/steps.py` functions
2. Add tests in `tests/test_steps.py` using MagicMock for obs, yt
3. Verify ScheduleEngine tests still pass

### Debug a schedule
```bash
sqlite3 backend/scheduler.db "SELECT id, status, start_at FROM schedule LIMIT 5;"
sqlite3 backend/scheduler.db "SELECT id, schedule_id, event, timestamp FROM run_log ORDER BY id DESC LIMIT 20;"
```

## Implementation Plan Phases

- **Phase 0–1**: Backend scaffolding, models, DB (✓ in plan)
- **Phase 2**: RRULE recurrence calculation (✓ in plan)
- **Phase 3**: OBS + YouTube clients (✓ in plan)
- **Phase 4**: Execution steps + APScheduler engine (✓ in plan)
- **Phase 5**: REST API + OAuth (✓ in plan)
- **Phase 6**: Frontend React app (✓ in plan)

See `docs/superpowers/plans/` for detailed task breakdowns with checkpoints.
