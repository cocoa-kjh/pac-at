### Task 9: OAuth 인증 라우터 & 상태 엔드포인트 & lifespan 구성

**Files:**
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/routers/status.py`
- Modify: `backend/app/main.py` (lifespan: DB init, OBS/YouTube/Engine 구성, 라우터 등록, CORS)
- Create: `backend/tests/test_api_status.py`

**Interfaces:**
- Consumes: `settings`, `OBSClient`, `build_youtube`, `YouTubeClient`, `ScheduleEngine`, APScheduler
- Produces:
  - `GET /auth/youtube` → Google 동의 URL로 리다이렉트
  - `GET /auth/youtube/callback` → 토큰 교환, oauth_token 저장, "/" 리다이렉트
  - `GET /status` → `{"obs_connected": bool, "youtube_authed": bool, "next_schedule": {...}|None, "live": bool}`
- Produces: `load_credentials(db) -> Credentials | None` (auth.py 헬퍼)

- [ ] **Step 1: 실패 테스트 작성 (status만 단위 검증)**

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.db import Base, get_engine, SessionLocal
from app.main import app, get_db, get_obs_dep

@pytest.fixture
def client():
    engine = get_engine(":memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal.configure(bind=engine)
    def _get_db():
        db = SessionLocal()
        try: yield db
        finally: db.close()
    obs = MagicMock(); obs.is_streaming.return_value = False
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_obs_dep] = lambda: obs
    yield TestClient(app), obs
    app.dependency_overrides.clear()

def test_status_reports_no_youtube_when_no_token(client):
    c, _ = client
    r = c.get("/status")
    assert r.status_code == 200
    assert r.json()["youtube_authed"] is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_api_status.py -v`
Expected: FAIL — /status 없음 (404)

- [ ] **Step 3: status.py 구현**

`backend/app/routers/status.py`:
```python
from fastapi import APIRouter, Depends
from app.main import get_db, get_obs_dep
from app.models import OAuthToken, Schedule

router = APIRouter(tags=["status"])

@router.get("/status")
def status(db=Depends(get_db), obs=Depends(get_obs_dep)):
    token = db.query(OAuthToken).first()
    nxt = (db.query(Schedule)
             .filter(Schedule.status == "pending")
             .order_by(Schedule.start_at).first())
    try:
        obs_connected = obs.is_streaming() is not None
    except Exception:
        obs_connected = False
    return {
        "obs_connected": obs_connected,
        "youtube_authed": token is not None,
        "next_schedule": {"id": nxt.id, "start_at": nxt.start_at.isoformat()} if nxt else None,
        "live": bool(token) and False,
    }
```

- [ ] **Step 4: auth.py 구현**

`backend/app/routers/auth.py`:
```python
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from app.main import get_db
from app.config import settings
from app.models import OAuthToken

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
REDIRECT_URI = f"http://localhost:{settings.port}/auth/youtube/callback"

router = APIRouter(tags=["auth"])

def _flow():
    return Flow.from_client_secrets_file(
        settings.client_secret_path, scopes=SCOPES, redirect_uri=REDIRECT_URI)

@router.get("/auth/youtube")
def youtube_auth():
    flow = _flow()
    url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                    include_granted_scopes="true")
    return RedirectResponse(url)

@router.get("/auth/youtube/callback")
def youtube_callback(request: Request, db=Depends(get_db)):
    flow = _flow()
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    token = db.query(OAuthToken).first() or OAuthToken()
    token.access_token = creds.token
    token.refresh_token = creds.refresh_token
    token.expiry = creds.expiry
    token.scopes = " ".join(creds.scopes or SCOPES)
    db.add(token); db.commit()
    return RedirectResponse("http://localhost:5173/")

def load_credentials(db) -> Credentials | None:
    token = db.query(OAuthToken).first()
    if not token or not token.refresh_token:
        return None
    import json
    with open(settings.client_secret_path) as f:
        cfg = json.load(f)["web"]
    return Credentials(
        token=token.access_token, refresh_token=token.refresh_token,
        token_uri=cfg["token_uri"], client_id=cfg["client_id"],
        client_secret=cfg["client_secret"], scopes=(token.scopes or "").split())
```

- [ ] **Step 5: main.py에 lifespan + 라우터 + CORS 구성**

`backend/app/main.py` 전체를 다음으로 교체:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.db import SessionLocal, get_engine, init_db
from app.config import settings
from app.clients.obs_client import OBSClient
from app.scheduler.engine import ScheduleEngine

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_engine_dep():
    return app.state.engine

def get_youtube_dep():
    return app.state.youtube

def get_obs_dep():
    return app.state.obs

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine(settings.db_path)
    init_db(engine)
    obs = OBSClient(settings.obs_host, settings.obs_port, settings.obs_password)
    try:
        obs.connect()
    except Exception:
        pass
    app.state.obs = obs
    app.state.youtube = _build_youtube_client()
    scheduler = BackgroundScheduler(); scheduler.start()
    app.state.engine = ScheduleEngine(scheduler, obs, app.state.youtube, SessionLocal)
    app.state.engine.load_pending()
    yield
    scheduler.shutdown(wait=False)

def _build_youtube_client():
    from app.routers.auth import load_credentials
    from app.clients.youtube_client import build_youtube, YouTubeClient
    db = SessionLocal()
    try:
        creds = load_credentials(db)
        return YouTubeClient(build_youtube(creds)) if creds else None
    finally:
        db.close()

app = FastAPI(title="YT Livestream Scheduler", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

from app.routers import broadcasts, scenes, schedules, auth, status  # noqa: E402
app.include_router(broadcasts.router)
app.include_router(scenes.router)
app.include_router(schedules.router)
app.include_router(auth.router)
app.include_router(status.router)
```

- [ ] **Step 6: 전체 백엔드 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest -v`
Expected: PASS (모든 테스트 통과)

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/auth.py backend/app/routers/status.py backend/app/main.py backend/tests/test_api_status.py
git commit -m "feat: OAuth 인증, 상태 엔드포인트, lifespan 구성 추가"
```

---

## Phase 6 — 프론트엔드

