# YouTube 라이브스트리밍 스케쥴러 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로컬 맥에서 YouTube Live 방송을 예약·생성하고 지정 시각에 OBS를 WebSocket으로 제어해 자동 송출·종료하는 개인용 웹앱을 구축한다.

**Architecture:** Python+FastAPI 백엔드가 SQLite에 스케쥴/방송/씬을 저장하고 APScheduler로 실행 엔진을 돌린다. 백엔드는 `OBSClient`(obs-websocket v5)와 `YouTubeClient`(Data API v3)를 통해 외부와 연동한다. React+Vite+TS SPA가 REST/WebSocket으로 백엔드와 통신한다.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, APScheduler, obs-websocket-py, google-api-python-client, SQLite, pytest / React 18, Vite, TypeScript, Vitest

## Global Constraints

- 실행 환경: 로컬 맥, localhost 전용 (외부 접속/배포 없음)
- 백엔드 포트 8000, 프론트엔드 포트 5173
- 단일 YouTube 계정, 멀티유저/권한 관리 없음
- 시크릿/토큰/DB 파일은 절대 커밋 금지 (`.gitignore` 이미 적용됨: `client_secret_*.json`, `*token*.json`, `*.db`, `.env*`)
- OAuth 스코프: `https://www.googleapis.com/auth/youtube.force-ssl`
- OBS WebSocket: `ws://localhost:4455`, obs-websocket **v5** 프로토콜
- 모든 시각은 UTC로 저장, 표시 시 로컬 변환
- 반복 규칙은 RFC 5545 RRULE 문자열로 저장
- TDD 필수: 실패 테스트 → 최소 구현 → 통과 → 커밋
- 외부 API(OBS/YouTube)는 클라이언트 클래스로 캡슐화하여 테스트에서 모킹

---

## File Structure

```
backend/
├─ pyproject.toml                # 의존성 정의
├─ app/
│  ├─ __init__.py
│  ├─ main.py                    # FastAPI 앱 진입점, 라우터 등록, lifespan
│  ├─ config.py                  # 설정(경로, 포트, OBS 주소 등)
│  ├─ db.py                      # SQLAlchemy 엔진/세션
│  ├─ models.py                  # ORM 모델 (6개 테이블)
│  ├─ schemas.py                 # Pydantic 입출력 스키마
│  ├─ clients/
│  │  ├─ __init__.py
│  │  ├─ obs_client.py           # OBSClient
│  │  └─ youtube_client.py       # YouTubeClient
│  ├─ scheduler/
│  │  ├─ __init__.py
│  │  ├─ engine.py               # APScheduler 래퍼, 등록/취소
│  │  ├─ steps.py                # 실행 단계 함수들
│  │  └─ recurrence.py           # RRULE 다음 시각 계산
│  ├─ routers/
│  │  ├─ __init__.py
│  │  ├─ auth.py                 # /auth/youtube*
│  │  ├─ broadcasts.py           # /broadcasts*
│  │  ├─ schedules.py            # /schedules*
│  │  ├─ scenes.py               # /scenes*
│  │  └─ status.py               # /status, WebSocket
│  └─ crud.py                    # DB 헬퍼 (생성/조회/갱신)
└─ tests/
   ├─ conftest.py                # 인메모리 DB fixture, 모킹
   ├─ test_models.py
   ├─ test_recurrence.py
   ├─ test_obs_client.py
   ├─ test_youtube_client.py
   ├─ test_steps.py
   ├─ test_engine.py
   └─ test_api_*.py

frontend/
├─ package.json
├─ vite.config.ts
├─ index.html
├─ src/
│  ├─ main.tsx
│  ├─ App.tsx
│  ├─ api/client.ts              # fetch 래퍼
│  ├─ types.ts                   # 백엔드 스키마 대응 타입
│  ├─ pages/
│  │  ├─ Dashboard.tsx
│  │  ├─ Broadcasts.tsx
│  │  ├─ Schedules.tsx
│  │  ├─ Scenes.tsx
│  │  └─ Settings.tsx
│  └─ components/
│     └─ SequenceEditor.tsx
└─ tests/
   └─ *.test.tsx
```

---

## Phase 0 — 백엔드 스캐폴딩

### Task 0: 백엔드 프로젝트 초기화

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`

**Interfaces:**
- Produces: `app.config.settings` — `Settings` 인스턴스 (`db_path: str`, `obs_host: str`, `obs_port: int`, `obs_password: str | None`, `port: int`, `client_secret_path: str`)

- [ ] **Step 1: pyproject.toml 작성**

```toml
[project]
name = "yt-livestream-scheduler"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy>=2.0",
    "apscheduler>=3.10",
    "obsws-python>=1.6",
    "google-api-python-client>=2.120",
    "google-auth-oauthlib>=1.2",
    "python-dateutil>=2.9",
    "pydantic>=2.6",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27"]

[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
```

- [ ] **Step 2: config.py 작성**

```python
from dataclasses import dataclass
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    db_path: str = os.getenv("DB_PATH", str(BASE_DIR / "scheduler.db"))
    obs_host: str = os.getenv("OBS_HOST", "localhost")
    obs_port: int = int(os.getenv("OBS_PORT", "4455"))
    obs_password: str | None = os.getenv("OBS_PASSWORD") or None
    port: int = int(os.getenv("PORT", "8000"))
    client_secret_path: str = os.getenv(
        "CLIENT_SECRET_PATH",
        str(BASE_DIR.parent / "_doc" /
            "client_secret_95002751475-aa4krs09rj7ul96q80nbbn8dokc9t8v4.apps.googleusercontent.com.json"),
    )

settings = Settings()
```

- [ ] **Step 3: 빈 `app/__init__.py`, `tests/__init__.py` 생성** (내용 없음)

- [ ] **Step 4: 의존성 설치 확인**

Run: `cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"`
Expected: 설치 성공, 에러 없음

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/config.py backend/tests/__init__.py
git commit -m "chore: 백엔드 프로젝트 스캐폴딩 및 설정"
```

---

## Phase 1 — 데이터 모델 & DB

### Task 1: SQLAlchemy 모델 정의

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `app.db.Base`, `app.db.get_engine(db_path)`, `app.db.SessionLocal`, `app.db.init_db(engine)`
- Produces 모델: `OAuthToken`, `Scene`, `Broadcast`, `Schedule`, `SequenceItem`, `RunLog` (필드는 스펙 4절 그대로)

- [ ] **Step 1: db.py 작성**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

def get_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

def init_db(engine):
    Base.metadata.create_all(bind=engine)
    SessionLocal.configure(bind=engine)
```

- [ ] **Step 2: 실패 테스트 작성 (conftest + test_models)**

`backend/tests/conftest.py`:
```python
import pytest
from app.db import Base, get_engine, SessionLocal

@pytest.fixture
def db():
    engine = get_engine(":memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal.configure(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
```

`backend/tests/test_models.py`:
```python
from datetime import datetime, timezone
from app.models import Broadcast, Schedule, Scene, SequenceItem

def test_create_broadcast_and_schedule(db):
    b = Broadcast(title="테스트", privacy="private", status="draft")
    db.add(b); db.commit()
    s = Schedule(broadcast_id=b.id,
                 start_at=datetime(2026, 7, 1, 11, tzinfo=timezone.utc),
                 end_at=datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
                 recurrence="none", status="pending")
    db.add(s); db.commit()
    assert s.id is not None
    assert s.broadcast_id == b.id

def test_sequence_item_links_scene(db):
    b = Broadcast(title="t", privacy="private", status="draft"); db.add(b); db.commit()
    s = Schedule(broadcast_id=b.id,
                 start_at=datetime(2026,7,1,tzinfo=timezone.utc),
                 end_at=datetime(2026,7,1,1,tzinfo=timezone.utc),
                 recurrence="none", status="pending"); db.add(s); db.commit()
    sc = Scene(name="인트로", obs_scene_name="Intro"); db.add(sc); db.commit()
    item = SequenceItem(schedule_id=s.id, scene_id=sc.id, order_index=0, duration_seconds=60)
    db.add(item); db.commit()
    assert item.order_index == 0
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_models.py -v`
Expected: FAIL — `app.models` 없음 (ImportError)

- [ ] **Step 4: models.py 작성**

```python
from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, Text, DateTime, ForeignKey)
from sqlalchemy.orm import relationship
from app.db import Base

def _utcnow():
    return datetime.now(timezone.utc)

class OAuthToken(Base):
    __tablename__ = "oauth_token"
    id = Column(Integer, primary_key=True)
    access_token = Column(Text)
    refresh_token = Column(Text)
    expiry = Column(DateTime)
    scopes = Column(Text)

class Scene(Base):
    __tablename__ = "scene"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    obs_scene_name = Column(String, nullable=False)
    note = Column(Text, default="")

class Broadcast(Base):
    __tablename__ = "broadcast"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    privacy = Column(String, default="private")   # public/unlisted/private
    youtube_broadcast_id = Column(String)
    youtube_stream_key = Column(String)
    status = Column(String, default="draft")       # draft/scheduled/live/completed/error
    schedules = relationship("Schedule", back_populates="broadcast")

class Schedule(Base):
    __tablename__ = "schedule"
    id = Column(Integer, primary_key=True)
    broadcast_id = Column(Integer, ForeignKey("broadcast.id"), nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    recurrence = Column(String, default="none")    # none/daily/weekly/...
    recurrence_rule = Column(Text)                 # RRULE
    status = Column(String, default="pending")     # pending/running/done/canceled
    broadcast = relationship("Broadcast", back_populates="schedules")
    items = relationship("SequenceItem", back_populates="schedule",
                         order_by="SequenceItem.order_index")

class SequenceItem(Base):
    __tablename__ = "sequence_item"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedule.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scene.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    duration_seconds = Column(Integer)             # None = end_at까지
    schedule = relationship("Schedule", back_populates="items")
    scene = relationship("Scene")

class RunLog(Base):
    __tablename__ = "run_log"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedule.id"))
    event = Column(String, nullable=False)
    detail = Column(Text, default="")
    timestamp = Column(DateTime, default=_utcnow)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/db.py backend/app/models.py backend/tests/conftest.py backend/tests/test_models.py
git commit -m "feat: SQLite 데이터 모델 6개 테이블 추가"
```

---

## Phase 2 — 반복 규칙 계산

### Task 2: RRULE 다음 발생 시각 계산

**Files:**
- Create: `backend/app/scheduler/__init__.py`
- Create: `backend/app/scheduler/recurrence.py`
- Create: `backend/tests/test_recurrence.py`

**Interfaces:**
- Produces: `next_occurrence(rrule: str | None, after: datetime) -> datetime | None` — RRULE이 None/빈문자면 None 반환, 아니면 `after` 이후 첫 발생 시각(UTC)

- [ ] **Step 1: 빈 `app/scheduler/__init__.py` 생성**

- [ ] **Step 2: 실패 테스트 작성**

```python
from datetime import datetime, timezone
from app.scheduler.recurrence import next_occurrence

def test_none_rule_returns_none():
    assert next_occurrence(None, datetime(2026,7,1,tzinfo=timezone.utc)) is None
    assert next_occurrence("", datetime(2026,7,1,tzinfo=timezone.utc)) is None

def test_weekly_rule_next_monday():
    # 2026-07-01 수요일 기준, 매주 월요일 09:00 UTC
    rule = "DTSTART:20260629T090000Z\nRRULE:FREQ=WEEKLY;BYDAY=MO"
    after = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    nxt = next_occurrence(rule, after)
    assert nxt == datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_recurrence.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 4: recurrence.py 구현**

```python
from datetime import datetime, timezone
from dateutil import rrule as _rrule

def next_occurrence(rrule: str | None, after: datetime) -> datetime | None:
    if not rrule:
        return None
    if after.tzinfo is None:
        after = after.replace(tzinfo=timezone.utc)
    rs = _rrule.rrulestr(rrule, forceset=True)
    nxt = rs.after(after, inc=False)
    if nxt is None:
        return None
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=timezone.utc)
    return nxt.astimezone(timezone.utc)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_recurrence.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler/__init__.py backend/app/scheduler/recurrence.py backend/tests/test_recurrence.py
git commit -m "feat: RRULE 다음 발생 시각 계산 추가"
```

---

## Phase 3 — 외부 클라이언트

### Task 3: OBSClient

**Files:**
- Create: `backend/app/clients/__init__.py`
- Create: `backend/app/clients/obs_client.py`
- Create: `backend/tests/test_obs_client.py`

**Interfaces:**
- Produces: `OBSClient(host, port, password)` with methods:
  - `connect() -> None`, `disconnect() -> None`
  - `list_scenes() -> list[str]`
  - `switch_scene(scene_name: str) -> None`
  - `set_stream_key(rtmp_url: str, stream_key: str) -> None`  (SetStreamServiceSettings)
  - `start_stream() -> None`, `stop_stream() -> None`
  - `is_streaming() -> bool`
- 내부적으로 `obsws-python`의 `ReqClient`를 래핑. 생성자는 `req_factory` 인자(기본 `obsws.ReqClient`)를 받아 테스트에서 모킹.

- [ ] **Step 1: 빈 `app/clients/__init__.py` 생성**

- [ ] **Step 2: 실패 테스트 작성**

```python
from unittest.mock import MagicMock
from app.clients.obs_client import OBSClient

def make_client():
    fake_req = MagicMock()
    factory = MagicMock(return_value=fake_req)
    c = OBSClient("localhost", 4455, None, req_factory=factory)
    c.connect()
    return c, fake_req

def test_list_scenes():
    c, req = make_client()
    req.get_scene_list.return_value = MagicMock(scenes=[{"sceneName": "Intro"}, {"sceneName": "Main"}])
    assert c.list_scenes() == ["Intro", "Main"]

def test_switch_scene_calls_set_program_scene():
    c, req = make_client()
    c.switch_scene("Main")
    req.set_current_program_scene.assert_called_once_with("Main")

def test_set_stream_key_calls_settings():
    c, req = make_client()
    c.set_stream_key("rtmp://a.rtmp.youtube.com/live2", "abcd-key")
    req.set_stream_service_settings.assert_called_once()

def test_start_and_stop_stream():
    c, req = make_client()
    c.start_stream(); req.start_stream.assert_called_once()
    c.stop_stream(); req.stop_stream.assert_called_once()
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_obs_client.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 4: obs_client.py 구현**

```python
from __future__ import annotations

def _default_factory(host, port, password):
    import obsws_python as obs
    return obs.ReqClient(host=host, port=port, password=password, timeout=5)

class OBSClient:
    def __init__(self, host: str, port: int, password: str | None, req_factory=None):
        self._host, self._port, self._password = host, port, password
        self._factory = req_factory or _default_factory
        self._req = None

    def connect(self) -> None:
        if self._factory is _default_factory:
            self._req = self._factory(self._host, self._port, self._password)
        else:
            self._req = self._factory()

    def disconnect(self) -> None:
        if self._req and hasattr(self._req, "disconnect"):
            self._req.disconnect()
        self._req = None

    def list_scenes(self) -> list[str]:
        resp = self._req.get_scene_list()
        return [s["sceneName"] for s in resp.scenes]

    def switch_scene(self, scene_name: str) -> None:
        self._req.set_current_program_scene(scene_name)

    def set_stream_key(self, rtmp_url: str, stream_key: str) -> None:
        settings = {"server": rtmp_url, "key": stream_key}
        self._req.set_stream_service_settings("rtmp_custom", settings)

    def start_stream(self) -> None:
        self._req.start_stream()

    def stop_stream(self) -> None:
        self._req.stop_stream()

    def is_streaming(self) -> bool:
        return bool(self._req.get_stream_status().output_active)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_obs_client.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/clients/__init__.py backend/app/clients/obs_client.py backend/tests/test_obs_client.py
git commit -m "feat: OBS WebSocket 클라이언트 추가"
```

---

### Task 4: YouTubeClient

**Files:**
- Create: `backend/app/clients/youtube_client.py`
- Create: `backend/tests/test_youtube_client.py`

**Interfaces:**
- Produces: `YouTubeClient(youtube_resource)` — 생성자는 google-api-python-client의 `build()` 결과(또는 모킹)를 주입받음. methods:
  - `create_broadcast(title, description, privacy, start_time: datetime) -> str`  (broadcast id 반환)
  - `create_stream(title: str) -> tuple[str, str, str]`  (stream_id, stream_key, ingestion_url 반환)
  - `bind(broadcast_id: str, stream_id: str) -> None`
  - `transition(broadcast_id: str, status: str) -> None`  (status: "live"|"complete"|"testing")
- Produces: `build_youtube(credentials) -> Resource` — `googleapiclient.discovery.build("youtube","v3",credentials=...)` 래퍼

- [ ] **Step 1: 실패 테스트 작성**

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.clients.youtube_client import YouTubeClient

def test_create_broadcast_returns_id():
    yt = MagicMock()
    yt.liveBroadcasts().insert().execute.return_value = {"id": "bc123"}
    client = YouTubeClient(yt)
    bid = client.create_broadcast("제목", "설명", "private",
                                  datetime(2026,7,1,tzinfo=timezone.utc))
    assert bid == "bc123"

def test_create_stream_returns_key_and_url():
    yt = MagicMock()
    yt.liveStreams().insert().execute.return_value = {
        "id": "st1",
        "cdn": {"ingestionInfo": {"streamName": "key-xyz",
                                  "ingestionAddress": "rtmp://a.rtmp.youtube.com/live2"}}}
    client = YouTubeClient(yt)
    sid, key, url = client.create_stream("내 스트림")
    assert (sid, key, url) == ("st1", "key-xyz", "rtmp://a.rtmp.youtube.com/live2")

def test_transition_calls_api():
    yt = MagicMock()
    client = YouTubeClient(yt)
    client.transition("bc123", "live")
    yt.liveBroadcasts().transition.assert_called()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_youtube_client.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: youtube_client.py 구현**

```python
from __future__ import annotations
from datetime import datetime

def build_youtube(credentials):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)

class YouTubeClient:
    def __init__(self, youtube_resource):
        self._yt = youtube_resource

    def create_broadcast(self, title: str, description: str, privacy: str,
                         start_time: datetime) -> str:
        body = {
            "snippet": {"title": title, "description": description,
                        "scheduledStartTime": start_time.isoformat()},
            "status": {"privacyStatus": privacy,
                       "selfDeclaredMadeForKids": False},
            "contentDetails": {"enableAutoStart": False, "enableAutoStop": False},
        }
        resp = self._yt.liveBroadcasts().insert(
            part="snippet,status,contentDetails", body=body).execute()
        return resp["id"]

    def create_stream(self, title: str) -> tuple[str, str, str]:
        body = {"snippet": {"title": title},
                "cdn": {"frameRate": "variable", "ingestionType": "rtmp",
                        "resolution": "variable"}}
        resp = self._yt.liveStreams().insert(
            part="snippet,cdn", body=body).execute()
        info = resp["cdn"]["ingestionInfo"]
        return resp["id"], info["streamName"], info["ingestionAddress"]

    def bind(self, broadcast_id: str, stream_id: str) -> None:
        self._yt.liveBroadcasts().bind(
            id=broadcast_id, part="id,contentDetails", streamId=stream_id).execute()

    def transition(self, broadcast_id: str, status: str) -> None:
        self._yt.liveBroadcasts().transition(
            broadcastStatus=status, id=broadcast_id, part="id,status").execute()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_youtube_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/clients/youtube_client.py backend/tests/test_youtube_client.py
git commit -m "feat: YouTube Data API 클라이언트 추가"
```

---

## Phase 4 — 실행 단계 & 엔진

### Task 5: 실행 단계 함수

**Files:**
- Create: `backend/app/crud.py`
- Create: `backend/app/scheduler/steps.py`
- Create: `backend/tests/test_steps.py`

**Interfaces:**
- Consumes: `OBSClient`, `YouTubeClient`, 모델
- Produces (`app.crud`): `log_run(db, schedule_id, event, detail="") -> RunLog`, `set_broadcast_status(db, broadcast_id, status) -> None`, `set_schedule_status(db, schedule_id, status) -> None`
- Produces (`app.scheduler.steps`):
  - `go_live(db, obs, yt, schedule) -> None` — 전체 시작 시퀀스 (YouTube live 전환 → 스트림키 OBS 주입 → start_stream → 첫 씬 전환)
  - `switch_to_item(obs, schedule, index) -> None` — index번째 sequence_item 씬으로 전환
  - `go_complete(db, obs, yt, schedule) -> None` — stop_stream → YouTube complete → 상태 갱신
  - 각 함수는 예외 발생 시 `set_*_status(..., "error")` + `log_run` 후 재전파

- [ ] **Step 1: crud.py 작성**

```python
from app.models import RunLog, Broadcast, Schedule

def log_run(db, schedule_id, event, detail=""):
    entry = RunLog(schedule_id=schedule_id, event=event, detail=detail)
    db.add(entry); db.commit()
    return entry

def set_broadcast_status(db, broadcast_id, status):
    b = db.get(Broadcast, broadcast_id)
    b.status = status; db.commit()

def set_schedule_status(db, schedule_id, status):
    s = db.get(Schedule, schedule_id)
    s.status = status; db.commit()
```

- [ ] **Step 2: 실패 테스트 작성**

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.models import Broadcast, Schedule, Scene, SequenceItem
from app.scheduler import steps

def _seed(db):
    b = Broadcast(title="t", privacy="private", status="scheduled",
                  youtube_broadcast_id="bc1", youtube_stream_key="key1")
    db.add(b); db.commit()
    s = Schedule(broadcast_id=b.id,
                 start_at=datetime(2026,7,1,tzinfo=timezone.utc),
                 end_at=datetime(2026,7,1,1,tzinfo=timezone.utc),
                 recurrence="none", status="pending"); db.add(s); db.commit()
    sc = Scene(name="메인", obs_scene_name="Main"); db.add(sc); db.commit()
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc.id, order_index=0,
                        duration_seconds=None)); db.commit()
    return b, s

def test_go_live_runs_full_sequence(db):
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    s.broadcast.youtube_stream_key = "key1"
    steps.go_live(db, obs, yt, s)
    yt.transition.assert_called_with("bc1", "live")
    obs.set_stream_key.assert_called_once()
    obs.start_stream.assert_called_once()
    obs.switch_scene.assert_called_with("Main")
    db.refresh(b)
    assert b.status == "live"

def test_go_complete_stops_and_completes(db):
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    steps.go_complete(db, obs, yt, s)
    obs.stop_stream.assert_called_once()
    yt.transition.assert_called_with("bc1", "complete")
    db.refresh(b)
    assert b.status == "completed"

def test_go_live_error_sets_error_status(db):
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    obs.start_stream.side_effect = RuntimeError("OBS 연결 실패")
    try:
        steps.go_live(db, obs, yt, s)
    except RuntimeError:
        pass
    db.refresh(b)
    assert b.status == "error"
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_steps.py -v`
Expected: FAIL — `app.scheduler.steps` 없음

- [ ] **Step 4: steps.py 구현**

```python
from app import crud

# YouTube 표준 RTMP. 스트림 생성 시 받은 ingestion_url을 broadcast에 저장해
# 두는 것이 이상적이나, 본 단계에서는 broadcast.youtube_stream_key를 사용하고
# RTMP URL은 표준 주소를 사용한다.
DEFAULT_RTMP = "rtmp://a.rtmp.youtube.com/live2"

def go_live(db, obs, yt, schedule):
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_live_start")
        yt.transition(b.youtube_broadcast_id, "live")
        obs.set_stream_key(DEFAULT_RTMP, b.youtube_stream_key)
        obs.start_stream()
        switch_to_item(obs, schedule, 0)
        crud.set_broadcast_status(db, b.id, "live")
        crud.set_schedule_status(db, schedule.id, "running")
        crud.log_run(db, schedule.id, "go_live_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_live_error", str(e))
        raise

def switch_to_item(obs, schedule, index):
    items = schedule.items
    if index < 0 or index >= len(items):
        return
    obs.switch_scene(items[index].scene.obs_scene_name)

def go_complete(db, obs, yt, schedule):
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_complete_start")
        try:
            obs.stop_stream()
        finally:
            yt.transition(b.youtube_broadcast_id, "complete")
        crud.set_broadcast_status(db, b.id, "completed")
        crud.set_schedule_status(db, schedule.id, "done")
        crud.log_run(db, schedule.id, "go_complete_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_complete_error", str(e))
        raise
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_steps.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/crud.py backend/app/scheduler/steps.py backend/tests/test_steps.py
git commit -m "feat: 방송 시작/종료 실행 단계 함수 추가"
```

---

### Task 6: 스케쥴 엔진 (APScheduler 래퍼)

**Files:**
- Create: `backend/app/scheduler/engine.py`
- Create: `backend/tests/test_engine.py`

**Interfaces:**
- Consumes: `next_occurrence`, `steps`, 모델
- Produces: `ScheduleEngine(scheduler, obs, yt, session_factory)` with:
  - `register(schedule_id: int) -> None` — DB에서 schedule 로드, start_at에 go_live 잡, end_at에 go_complete 잡, 시퀀스 중간 전환 잡 등록. 반복이면 다음 occurrence도 예약
  - `cancel(schedule_id: int) -> None` — 관련 잡 제거, status=canceled
  - `load_pending() -> None` — DB의 status=pending 스케쥴 모두 register
  - 잡 id 규칙: `f"sched:{id}:live"`, `f"sched:{id}:complete"`, `f"sched:{id}:item:{n}"`
- `scheduler`는 APScheduler `BackgroundScheduler` 인스턴스(테스트에선 MagicMock)

- [ ] **Step 1: 실패 테스트 작성**

```python
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.models import Broadcast, Schedule, Scene, SequenceItem
from app.scheduler.engine import ScheduleEngine

def _seed_two_items(db):
    b = Broadcast(title="t", privacy="private", status="scheduled",
                  youtube_broadcast_id="bc1", youtube_stream_key="k1"); db.add(b); db.commit()
    start = datetime(2026,7,1,9,tzinfo=timezone.utc)
    s = Schedule(broadcast_id=b.id, start_at=start, end_at=start+timedelta(hours=1),
                 recurrence="none", status="pending"); db.add(s); db.commit()
    sc1 = Scene(name="인트로", obs_scene_name="Intro"); db.add(sc1)
    sc2 = Scene(name="메인", obs_scene_name="Main"); db.add(sc2); db.commit()
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc1.id, order_index=0, duration_seconds=60))
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc2.id, order_index=1, duration_seconds=None))
    db.commit()
    return s

def test_register_adds_live_and_complete_jobs(db):
    from app.db import SessionLocal
    s = _seed_two_items(db)
    sched = MagicMock()
    eng = ScheduleEngine(sched, MagicMock(), MagicMock(), SessionLocal)
    eng.register(s.id)
    job_ids = [c.kwargs.get("id") or c.args[2] for c in sched.add_job.call_args_list]
    assert f"sched:{s.id}:live" in job_ids
    assert f"sched:{s.id}:complete" in job_ids
    # 두 번째 item(인트로 60초 후)에 대한 전환 잡 존재
    assert f"sched:{s.id}:item:1" in job_ids

def test_cancel_removes_jobs_and_sets_status(db):
    from app.db import SessionLocal
    s = _seed_two_items(db)
    sched = MagicMock()
    eng = ScheduleEngine(sched, MagicMock(), MagicMock(), SessionLocal)
    eng.register(s.id)
    eng.cancel(s.id)
    assert sched.remove_job.called
    db.refresh(s)
    assert s.status == "canceled"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_engine.py -v`
Expected: FAIL — `app.scheduler.engine` 없음

- [ ] **Step 3: engine.py 구현**

```python
from datetime import timedelta
from app.models import Schedule
from app.scheduler import steps
from app.scheduler.recurrence import next_occurrence

class ScheduleEngine:
    def __init__(self, scheduler, obs, yt, session_factory):
        self._sched = scheduler
        self._obs = obs
        self._yt = yt
        self._session_factory = session_factory

    def _run_go_live(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.go_live(db, self._obs, self._yt, s)
        finally:
            db.close()

    def _run_switch(self, schedule_id, index):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.switch_to_item(self._obs, s, index)
        finally:
            db.close()

    def _run_go_complete(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.go_complete(db, self._obs, self._yt, s)
            if s.recurrence_rule:
                nxt = next_occurrence(s.recurrence_rule, s.start_at)
                if nxt:
                    self._reschedule(s, nxt)
        finally:
            db.close()

    def _reschedule(self, schedule, new_start):
        duration = schedule.end_at - schedule.start_at
        schedule.start_at = new_start
        schedule.end_at = new_start + duration
        schedule.status = "pending"
        self.register(schedule.id)

    def register(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            self._sched.add_job(self._run_go_live, "date", run_date=s.start_at,
                                args=[s.id], id=f"sched:{s.id}:live",
                                replace_existing=True)
            # 시퀀스 중간 전환: order_index 0은 go_live에서 처리, 1부터 누적시간 계산
            offset = 0
            for item in s.items:
                if item.order_index == 0:
                    offset += item.duration_seconds or 0
                    continue
                run_at = s.start_at + timedelta(seconds=offset)
                self._sched.add_job(self._run_switch, "date", run_date=run_at,
                                    args=[s.id, item.order_index],
                                    id=f"sched:{s.id}:item:{item.order_index}",
                                    replace_existing=True)
                offset += item.duration_seconds or 0
            self._sched.add_job(self._run_go_complete, "date", run_date=s.end_at,
                                args=[s.id], id=f"sched:{s.id}:complete",
                                replace_existing=True)
        finally:
            db.close()

    def cancel(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            for jid in (f"sched:{schedule_id}:live", f"sched:{schedule_id}:complete"):
                try: self._sched.remove_job(jid)
                except Exception: pass
            for item in s.items:
                try: self._sched.remove_job(f"sched:{schedule_id}:item:{item.order_index}")
                except Exception: pass
            s.status = "canceled"; db.commit()
        finally:
            db.close()

    def load_pending(self):
        db = self._session_factory()
        try:
            ids = [s.id for s in db.query(Schedule).filter(Schedule.status == "pending").all()]
        finally:
            db.close()
        for sid in ids:
            self.register(sid)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_engine.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/engine.py backend/tests/test_engine.py
git commit -m "feat: APScheduler 기반 스케쥴 실행 엔진 추가"
```

---

## Phase 5 — REST API & 인증

### Task 7: Pydantic 스키마 & CRUD 라우터 (broadcasts, scenes, schedules)

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/broadcasts.py`
- Create: `backend/app/routers/scenes.py`
- Create: `backend/app/routers/schedules.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api_crud.py`

**Interfaces:**
- Consumes: 모델, `ScheduleEngine`, `YouTubeClient`
- Produces: FastAPI 앱 `app.main.app`, `app.main.get_db` 의존성, `app.main.get_engine_dep`(ScheduleEngine 의존성, 테스트에서 override)
- 엔드포인트:
  - `POST /broadcasts` body=`BroadcastCreate` → `BroadcastOut`; `GET /broadcasts`; `POST /broadcasts/{id}/youtube` (YouTube 이벤트+스트림 생성, bind, 키 저장)
  - `GET/POST /scenes`; `POST /scenes/sync` (OBS에서 씬 목록 동기화)
  - `GET/POST /schedules` (생성 시 sequence_items 포함, ScheduleEngine.register 호출); `DELETE /schedules/{id}` (engine.cancel)

- [ ] **Step 1: schemas.py 작성**

```python
from datetime import datetime
from pydantic import BaseModel

class BroadcastCreate(BaseModel):
    title: str
    description: str = ""
    privacy: str = "private"

class BroadcastOut(BroadcastCreate):
    id: int
    youtube_broadcast_id: str | None = None
    status: str
    class Config: from_attributes = True

class SceneCreate(BaseModel):
    name: str
    obs_scene_name: str
    note: str = ""

class SceneOut(SceneCreate):
    id: int
    class Config: from_attributes = True

class SequenceItemIn(BaseModel):
    scene_id: int
    order_index: int
    duration_seconds: int | None = None

class ScheduleCreate(BaseModel):
    broadcast_id: int
    start_at: datetime
    end_at: datetime
    recurrence: str = "none"
    recurrence_rule: str | None = None
    items: list[SequenceItemIn] = []

class ScheduleOut(BaseModel):
    id: int
    broadcast_id: int
    start_at: datetime
    end_at: datetime
    recurrence: str
    status: str
    class Config: from_attributes = True
```

- [ ] **Step 2: 실패 테스트 작성 (test_api_crud.py)**

```python
import pytest
from fastapi.testclient import TestClient
from app.db import Base, get_engine, SessionLocal
from app.main import app, get_db, get_engine_dep
from unittest.mock import MagicMock

@pytest.fixture
def client():
    engine = get_engine(":memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal.configure(bind=engine)
    def _get_db():
        db = SessionLocal()
        try: yield db
        finally: db.close()
    fake_engine = MagicMock()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_engine_dep] = lambda: fake_engine
    yield TestClient(app), fake_engine
    app.dependency_overrides.clear()

def test_create_and_list_broadcast(client):
    c, _ = client
    r = c.post("/broadcasts", json={"title": "내 방송", "privacy": "private"})
    assert r.status_code == 200
    assert r.json()["title"] == "내 방송"
    assert c.get("/broadcasts").json()[0]["title"] == "내 방송"

def test_create_scene(client):
    c, _ = client
    r = c.post("/scenes", json={"name": "메인", "obs_scene_name": "Main"})
    assert r.status_code == 200
    assert r.json()["obs_scene_name"] == "Main"

def test_create_schedule_registers_engine(client):
    c, eng = client
    bid = c.post("/broadcasts", json={"title": "b"}).json()["id"]
    sid_scene = c.post("/scenes", json={"name": "m", "obs_scene_name": "Main"}).json()["id"]
    r = c.post("/schedules", json={
        "broadcast_id": bid,
        "start_at": "2026-07-01T09:00:00+00:00",
        "end_at": "2026-07-01T10:00:00+00:00",
        "recurrence": "none",
        "items": [{"scene_id": sid_scene, "order_index": 0, "duration_seconds": None}],
    })
    assert r.status_code == 200
    eng.register.assert_called_once()

def test_delete_schedule_cancels(client):
    c, eng = client
    bid = c.post("/broadcasts", json={"title": "b"}).json()["id"]
    sid = c.post("/schedules", json={
        "broadcast_id": bid, "start_at": "2026-07-01T09:00:00+00:00",
        "end_at": "2026-07-01T10:00:00+00:00", "items": []}).json()["id"]
    r = c.delete(f"/schedules/{sid}")
    assert r.status_code == 200
    eng.cancel.assert_called_with(sid)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_api_crud.py -v`
Expected: FAIL — `app.main` 없음

- [ ] **Step 4: main.py + 라우터 구현**

`backend/app/main.py`:
```python
from fastapi import FastAPI, Depends
from app.db import SessionLocal

app = FastAPI(title="YT Livestream Scheduler")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# 실제 ScheduleEngine은 lifespan에서 구성. 기본 의존성은 앱 상태에서 가져옴.
def get_engine_dep():
    return app.state.engine

from app.routers import broadcasts, scenes, schedules  # noqa: E402
app.include_router(broadcasts.router)
app.include_router(scenes.router)
app.include_router(schedules.router)
```

`backend/app/routers/__init__.py`: (빈 파일)

`backend/app/routers/broadcasts.py`:
```python
from fastapi import APIRouter, Depends
from app.main import get_db
from app import schemas
from app.models import Broadcast

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])

@router.post("", response_model=schemas.BroadcastOut)
def create_broadcast(payload: schemas.BroadcastCreate, db=Depends(get_db)):
    b = Broadcast(**payload.model_dump()); db.add(b); db.commit(); db.refresh(b)
    return b

@router.get("", response_model=list[schemas.BroadcastOut])
def list_broadcasts(db=Depends(get_db)):
    return db.query(Broadcast).all()
```

`backend/app/routers/scenes.py`:
```python
from fastapi import APIRouter, Depends
from app.main import get_db
from app import schemas
from app.models import Scene

router = APIRouter(prefix="/scenes", tags=["scenes"])

@router.post("", response_model=schemas.SceneOut)
def create_scene(payload: schemas.SceneCreate, db=Depends(get_db)):
    s = Scene(**payload.model_dump()); db.add(s); db.commit(); db.refresh(s)
    return s

@router.get("", response_model=list[schemas.SceneOut])
def list_scenes(db=Depends(get_db)):
    return db.query(Scene).all()
```

`backend/app/routers/schedules.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from app.main import get_db, get_engine_dep
from app import schemas
from app.models import Schedule, SequenceItem

router = APIRouter(prefix="/schedules", tags=["schedules"])

@router.post("", response_model=schemas.ScheduleOut)
def create_schedule(payload: schemas.ScheduleCreate, db=Depends(get_db),
                    engine=Depends(get_engine_dep)):
    s = Schedule(broadcast_id=payload.broadcast_id, start_at=payload.start_at,
                 end_at=payload.end_at, recurrence=payload.recurrence,
                 recurrence_rule=payload.recurrence_rule, status="pending")
    db.add(s); db.commit(); db.refresh(s)
    for item in payload.items:
        db.add(SequenceItem(schedule_id=s.id, scene_id=item.scene_id,
                            order_index=item.order_index,
                            duration_seconds=item.duration_seconds))
    db.commit()
    engine.register(s.id)
    return s

@router.get("", response_model=list[schemas.ScheduleOut])
def list_schedules(db=Depends(get_db)):
    return db.query(Schedule).all()

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db=Depends(get_db),
                    engine=Depends(get_engine_dep)):
    s = db.get(Schedule, schedule_id)
    if not s: raise HTTPException(404)
    engine.cancel(schedule_id)
    return {"ok": True}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_api_crud.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/main.py backend/app/routers/ backend/tests/test_api_crud.py
git commit -m "feat: broadcasts/scenes/schedules REST API 추가"
```

---

### Task 8: YouTube 이벤트 생성 엔드포인트 & OBS 씬 동기화

**Files:**
- Modify: `backend/app/routers/broadcasts.py` (POST /broadcasts/{id}/youtube 추가)
- Modify: `backend/app/routers/scenes.py` (POST /scenes/sync 추가)
- Modify: `backend/app/main.py` (`get_youtube_dep`, `get_obs_dep` 의존성 추가)
- Create: `backend/tests/test_api_integrations.py`

**Interfaces:**
- Consumes: `YouTubeClient`, `OBSClient`
- Produces: `app.main.get_youtube_dep() -> YouTubeClient`, `app.main.get_obs_dep() -> OBSClient` (lifespan에서 `app.state`에 설정, 테스트에서 override)
- `POST /broadcasts/{id}/youtube`: create_broadcast → create_stream → bind → broadcast에 youtube_broadcast_id/youtube_stream_key 저장, status="scheduled"
- `POST /scenes/sync`: OBS list_scenes() → DB에 없는 씬을 obs_scene_name으로 추가

- [ ] **Step 1: main.py에 의존성 추가**

`backend/app/main.py`에 추가:
```python
def get_youtube_dep():
    return app.state.youtube

def get_obs_dep():
    return app.state.obs
```

- [ ] **Step 2: 실패 테스트 작성**

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.db import Base, get_engine, SessionLocal
from app.main import app, get_db, get_youtube_dep, get_obs_dep

@pytest.fixture
def client():
    engine = get_engine(":memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal.configure(bind=engine)
    def _get_db():
        db = SessionLocal()
        try: yield db
        finally: db.close()
    yt, obs = MagicMock(), MagicMock()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_youtube_dep] = lambda: yt
    app.dependency_overrides[get_obs_dep] = lambda: obs
    yield TestClient(app), yt, obs
    app.dependency_overrides.clear()

def test_create_youtube_event(client):
    c, yt, _ = client
    yt.create_broadcast.return_value = "bc1"
    yt.create_stream.return_value = ("st1", "key1", "rtmp://x")
    bid = c.post("/broadcasts", json={"title": "방송"}).json()["id"]
    r = c.post(f"/broadcasts/{bid}/youtube")
    assert r.status_code == 200
    body = r.json()
    assert body["youtube_broadcast_id"] == "bc1"
    assert body["status"] == "scheduled"
    yt.bind.assert_called_with("bc1", "st1")

def test_sync_scenes_from_obs(client):
    c, _, obs = client
    obs.list_scenes.return_value = ["Intro", "Main"]
    r = c.post("/scenes/sync")
    assert r.status_code == 200
    names = {s["obs_scene_name"] for s in c.get("/scenes").json()}
    assert names == {"Intro", "Main"}
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_api_integrations.py -v`
Expected: FAIL — 엔드포인트 없음 (404)

- [ ] **Step 4: 엔드포인트 구현**

`backend/app/routers/broadcasts.py`에 추가:
```python
from fastapi import HTTPException
from app.main import get_youtube_dep

@router.post("/{broadcast_id}/youtube", response_model=schemas.BroadcastOut)
def create_youtube_event(broadcast_id: int, db=Depends(get_db),
                         yt=Depends(get_youtube_dep)):
    b = db.get(Broadcast, broadcast_id)
    if not b: raise HTTPException(404)
    from datetime import datetime, timezone
    bid = yt.create_broadcast(b.title, b.description, b.privacy,
                              datetime.now(timezone.utc))
    stream_id, key, _url = yt.create_stream(f"{b.title} stream")
    yt.bind(bid, stream_id)
    b.youtube_broadcast_id = bid
    b.youtube_stream_key = key
    b.status = "scheduled"
    db.commit(); db.refresh(b)
    return b
```

`backend/app/routers/scenes.py`에 추가:
```python
from app.main import get_obs_dep

@router.post("/sync")
def sync_scenes(db=Depends(get_db), obs=Depends(get_obs_dep)):
    existing = {s.obs_scene_name for s in db.query(Scene).all()}
    for name in obs.list_scenes():
        if name not in existing:
            db.add(Scene(name=name, obs_scene_name=name))
    db.commit()
    return {"ok": True}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_api_integrations.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/broadcasts.py backend/app/routers/scenes.py backend/app/main.py backend/tests/test_api_integrations.py
git commit -m "feat: YouTube 이벤트 생성 및 OBS 씬 동기화 엔드포인트 추가"
```

---

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

### Task 10: 프론트엔드 스캐폴딩 & API 클라이언트

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/tests/client.test.ts`

**Interfaces:**
- Produces (`src/types.ts`): `Broadcast`, `Scene`, `Schedule`, `SequenceItem`, `Status` 타입 (백엔드 스키마 대응)
- Produces (`src/api/client.ts`): `api.listBroadcasts()`, `api.createBroadcast(data)`, `api.createYoutubeEvent(id)`, `api.listScenes()`, `api.syncScenes()`, `api.listSchedules()`, `api.createSchedule(data)`, `api.deleteSchedule(id)`, `api.getStatus()` — 모두 `fetch` 기반, baseURL `http://localhost:8000`

- [ ] **Step 1: package.json / vite / tsconfig / index.html 작성**

`frontend/package.json`:
```json
{
  "name": "yt-scheduler-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0"
  }
}
```

`frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], server: { port: 5173 } });
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020", "module": "ESNext", "moduleResolution": "bundler",
    "jsx": "react-jsx", "strict": true, "esModuleInterop": true,
    "skipLibCheck": true, "lib": ["ES2020", "DOM", "DOM.Iterable"]
  },
  "include": ["src", "tests"]
}
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="ko">
  <head><meta charset="UTF-8" /><title>YT 라이브 스케쥴러</title></head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
```

- [ ] **Step 2: types.ts 작성**

```typescript
export interface Broadcast {
  id: number; title: string; description: string; privacy: string;
  youtube_broadcast_id: string | null; status: string;
}
export interface Scene { id: number; name: string; obs_scene_name: string; note: string; }
export interface SequenceItem { scene_id: number; order_index: number; duration_seconds: number | null; }
export interface Schedule {
  id: number; broadcast_id: number; start_at: string; end_at: string;
  recurrence: string; status: string;
}
export interface Status {
  obs_connected: boolean; youtube_authed: boolean;
  next_schedule: { id: number; start_at: string } | null; live: boolean;
}
```

- [ ] **Step 3: 실패 테스트 작성 (client.test.ts)**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../src/api/client";

beforeEach(() => {
  global.fetch = vi.fn(async () =>
    ({ ok: true, json: async () => [{ id: 1, title: "t" }] }) as Response);
});

describe("api client", () => {
  it("listBroadcasts hits /broadcasts", async () => {
    const data = await api.listBroadcasts();
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/broadcasts", expect.any(Object));
    expect(data[0].id).toBe(1);
  });
  it("createSchedule POSTs JSON", async () => {
    await api.createSchedule({ broadcast_id: 1, start_at: "x", end_at: "y",
      recurrence: "none", recurrence_rule: null, items: [] } as any);
    const call = (global.fetch as any).mock.calls.at(-1);
    expect(call[1].method).toBe("POST");
  });
});
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd frontend && npm install && npx vitest run`
Expected: FAIL — `src/api/client` 없음

- [ ] **Step 5: client.ts 구현**

```typescript
import type { Broadcast, Scene, Schedule, Status } from "../types";
const BASE = "http://localhost:8000";

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

export const api = {
  listBroadcasts: () => req<Broadcast[]>("/broadcasts"),
  createBroadcast: (data: Partial<Broadcast>) =>
    req<Broadcast>("/broadcasts", { method: "POST", body: JSON.stringify(data) }),
  createYoutubeEvent: (id: number) =>
    req<Broadcast>(`/broadcasts/${id}/youtube`, { method: "POST" }),
  listScenes: () => req<Scene[]>("/scenes"),
  syncScenes: () => req<{ ok: boolean }>("/scenes/sync", { method: "POST" }),
  listSchedules: () => req<Schedule[]>("/schedules"),
  createSchedule: (data: any) =>
    req<Schedule>("/schedules", { method: "POST", body: JSON.stringify(data) }),
  deleteSchedule: (id: number) =>
    req<{ ok: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
  getStatus: () => req<Status>("/status"),
};
```

- [ ] **Step 6: main.tsx / App.tsx 최소 구현**

`frontend/src/main.tsx`:
```typescript
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
createRoot(document.getElementById("root")!).render(<App />);
```

`frontend/src/App.tsx`:
```typescript
export default function App() {
  return <div><h1>YT 라이브 스케쥴러</h1></div>;
}
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd frontend && npx vitest run`
Expected: PASS (2 passed)

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/ frontend/tests/
git commit -m "feat: 프론트엔드 스캐폴딩 및 API 클라이언트 추가"
```

---

### Task 11: 페이지 구성 (Dashboard / Broadcasts / Scenes / Schedules / Settings)

**Files:**
- Modify: `frontend/src/App.tsx` (라우터)
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Broadcasts.tsx`
- Create: `frontend/src/pages/Scenes.tsx`
- Create: `frontend/src/pages/Schedules.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/components/SequenceEditor.tsx`
- Create: `frontend/tests/Broadcasts.test.tsx`

**Interfaces:**
- Consumes: `api`, types
- Produces: 라우팅된 5개 페이지. `SequenceEditor`는 `value: SequenceItem[]`, `onChange(items)`, `scenes: Scene[]` props를 받아 씬 추가/순서/지속시간 편집.

- [ ] **Step 1: 실패 테스트 작성 (Broadcasts 페이지)**

`frontend/tests/Broadcasts.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Broadcasts from "../src/pages/Broadcasts";
import { api } from "../src/api/client";

vi.mock("../src/api/client");

beforeEach(() => {
  (api.listBroadcasts as any) = vi.fn(async () => [
    { id: 1, title: "내 방송", description: "", privacy: "private",
      youtube_broadcast_id: null, status: "draft" }]);
});

describe("Broadcasts page", () => {
  it("renders broadcast titles", async () => {
    render(<Broadcasts />);
    await waitFor(() => expect(screen.getByText("내 방송")).toBeDefined());
  });
});
```

추가 devDependency 필요: `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`.
`frontend/package.json`의 devDependencies에 추가하고 `frontend/vite.config.ts`에 `test: { environment: "jsdom" }` 추가.

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm install && npx vitest run tests/Broadcasts.test.tsx`
Expected: FAIL — `src/pages/Broadcasts` 없음

- [ ] **Step 3: Broadcasts.tsx 구현**

```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Broadcast } from "../types";

export default function Broadcasts() {
  const [items, setItems] = useState<Broadcast[]>([]);
  const [title, setTitle] = useState("");
  const reload = () => api.listBroadcasts().then(setItems);
  useEffect(() => { reload(); }, []);
  const create = async () => { await api.createBroadcast({ title }); setTitle(""); reload(); };
  return (
    <div>
      <h2>방송 관리</h2>
      <input value={title} onChange={e => setTitle(e.target.value)} placeholder="제목" />
      <button onClick={create}>방송 생성</button>
      <ul>{items.map(b => (
        <li key={b.id}>{b.title} — {b.status}
          {!b.youtube_broadcast_id &&
            <button onClick={() => api.createYoutubeEvent(b.id).then(reload)}>YouTube 이벤트 생성</button>}
        </li>))}</ul>
    </div>
  );
}
```

- [ ] **Step 4: 나머지 페이지 + SequenceEditor + App 라우터 구현**

`frontend/src/pages/Scenes.tsx`:
```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scene } from "../types";
export default function Scenes() {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const reload = () => api.listScenes().then(setScenes);
  useEffect(() => { reload(); }, []);
  return (
    <div><h2>씬 매핑</h2>
      <button onClick={() => api.syncScenes().then(reload)}>OBS 씬 동기화</button>
      <ul>{scenes.map(s => <li key={s.id}>{s.name} ({s.obs_scene_name})</li>)}</ul>
    </div>);
}
```

`frontend/src/components/SequenceEditor.tsx`:
```typescript
import type { Scene, SequenceItem } from "../types";
export default function SequenceEditor(
  { value, onChange, scenes }:
  { value: SequenceItem[]; onChange: (v: SequenceItem[]) => void; scenes: Scene[] }) {
  const add = (scene_id: number) =>
    onChange([...value, { scene_id, order_index: value.length, duration_seconds: 60 }]);
  const setDur = (i: number, d: number) =>
    onChange(value.map((it, idx) => idx === i ? { ...it, duration_seconds: d } : it));
  return (
    <div><h4>시퀀스 편성</h4>
      <select onChange={e => add(Number(e.target.value))} value="">
        <option value="" disabled>씬 추가...</option>
        {scenes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <ol>{value.map((it, i) => {
        const sc = scenes.find(s => s.id === it.scene_id);
        return <li key={i}>{sc?.name}
          <input type="number" value={it.duration_seconds ?? 0}
                 onChange={e => setDur(i, Number(e.target.value))} /> 초</li>;
      })}</ol>
    </div>);
}
```

`frontend/src/pages/Schedules.tsx`:
```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Schedule, Scene, Broadcast, SequenceItem } from "../types";
import SequenceEditor from "../components/SequenceEditor";

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [broadcastId, setBroadcastId] = useState<number | null>(null);
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [rrule, setRrule] = useState("");
  const [items, setItems] = useState<SequenceItem[]>([]);
  const reload = () => api.listSchedules().then(setSchedules);
  useEffect(() => {
    reload(); api.listScenes().then(setScenes); api.listBroadcasts().then(setBroadcasts);
  }, []);
  const create = async () => {
    if (broadcastId == null) return;
    await api.createSchedule({
      broadcast_id: broadcastId,
      start_at: new Date(startAt).toISOString(),
      end_at: new Date(endAt).toISOString(),
      recurrence: rrule ? "custom" : "none",
      recurrence_rule: rrule || null, items });
    setItems([]); reload();
  };
  return (
    <div><h2>스케쥴</h2>
      <select onChange={e => setBroadcastId(Number(e.target.value))} value={broadcastId ?? ""}>
        <option value="" disabled>방송 선택</option>
        {broadcasts.map(b => <option key={b.id} value={b.id}>{b.title}</option>)}
      </select>
      <label>시작 <input type="datetime-local" value={startAt} onChange={e => setStartAt(e.target.value)} /></label>
      <label>종료 <input type="datetime-local" value={endAt} onChange={e => setEndAt(e.target.value)} /></label>
      <label>RRULE <input value={rrule} onChange={e => setRrule(e.target.value)} placeholder="RRULE:FREQ=WEEKLY;BYDAY=MO" /></label>
      <SequenceEditor value={items} onChange={setItems} scenes={scenes} />
      <button onClick={create}>스케쥴 생성</button>
      <ul>{schedules.map(s => (
        <li key={s.id}>#{s.id} {s.start_at} — {s.status}
          <button onClick={() => api.deleteSchedule(s.id).then(reload)}>취소</button>
        </li>))}</ul>
    </div>);
}
```

`frontend/src/pages/Dashboard.tsx`:
```typescript
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Status } from "../types";
export default function Dashboard() {
  const [s, setS] = useState<Status | null>(null);
  useEffect(() => {
    const t = setInterval(() => api.getStatus().then(setS), 3000);
    api.getStatus().then(setS);
    return () => clearInterval(t);
  }, []);
  if (!s) return <div>로딩...</div>;
  return (
    <div><h2>대시보드</h2>
      <p>OBS: {s.obs_connected ? "●연결" : "○끊김"}</p>
      <p>YouTube: {s.youtube_authed ? "●인증" : "○미인증"}</p>
      <p>다음 방송: {s.next_schedule ? s.next_schedule.start_at : "없음"}</p>
      <p>현재 LIVE: {s.live ? "예" : "아니오"}</p>
    </div>);
}
```

`frontend/src/pages/Settings.tsx`:
```typescript
export default function Settings() {
  return (
    <div><h2>설정</h2>
      <a href="http://localhost:8000/auth/youtube">YouTube 연결/재인증</a>
    </div>);
}
```

`frontend/src/App.tsx`:
```typescript
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Broadcasts from "./pages/Broadcasts";
import Scenes from "./pages/Scenes";
import Schedules from "./pages/Schedules";
import Settings from "./pages/Settings";
export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ display: "flex", gap: 12 }}>
        <Link to="/">대시보드</Link><Link to="/broadcasts">방송</Link>
        <Link to="/schedules">스케쥴</Link><Link to="/scenes">씬</Link>
        <Link to="/settings">설정</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/broadcasts" element={<Broadcasts />} />
        <Route path="/schedules" element={<Schedules />} />
        <Route path="/scenes" element={<Scenes />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>);
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend && npx vitest run`
Expected: PASS (모든 테스트 통과)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ frontend/tests/ frontend/package.json frontend/vite.config.ts
git commit -m "feat: 프론트엔드 5개 페이지 및 시퀀스 에디터 추가"
```

---

## Phase 7 — 통합 & 문서

### Task 12: README & 수동 E2E 절차

**Files:**
- Create: `README.md`
- Create: `backend/.env.example`

**Interfaces:** 없음 (문서)

- [ ] **Step 1: backend/.env.example 작성**

```
# OBS WebSocket 비밀번호 (OBS > 도구 > WebSocket 서버 설정)
OBS_PASSWORD=
# 기본값이 맞으면 비워둠
OBS_HOST=localhost
OBS_PORT=4455
PORT=8000
```

- [ ] **Step 2: README.md 작성**

```markdown
# YouTube 라이브스트리밍 스케쥴러

로컬 맥에서 YouTube Live 방송을 예약하고 OBS를 자동 제어해 송출/종료한다.

## 사전 준비
1. OBS Studio 설치, 도구 > WebSocket 서버 설정에서 서버 활성화 (포트 4455)
2. 송출할 영상마다 씬을 만들고 미디어 소스 추가
3. Google Cloud 프로젝트에 OAuth 동의화면 + 본인 계정을 테스트 사용자로 등록
4. `_doc/client_secret_*.json` 위치 확인 (이미 존재)

## 실행
백엔드:
    cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/uvicorn app.main:app --port 8000
프론트엔드:
    cd frontend && npm install && npm run dev
브라우저에서 http://localhost:5173 접속.

## 최초 1회: YouTube 연결
설정 페이지 > "YouTube 연결" 클릭 → Google 동의 → 자동 복귀.

## 사용 흐름
1. 씬 페이지 > "OBS 씬 동기화"
2. 방송 페이지 > 방송 생성 > "YouTube 이벤트 생성"
3. 스케쥴 페이지 > 방송 선택, 시작/종료 시각, 시퀀스 편성 > 스케쥴 생성
4. 지정 시각에 자동으로 송출 시작 → 씬 전환 → 종료

## 테스트
    cd backend && .venv/bin/pytest
    cd frontend && npm test

## 수동 E2E (실제 OBS + private 방송)
1. private 방송으로 스케쥴 생성, 시작 시각을 2분 후로 설정
2. OBS 실행 상태 유지
3. 시작 시각에 OBS 스트리밍 시작 + 씬 전환 확인
4. YouTube 스튜디오에서 라이브 수신 확인
5. 종료 시각에 스트림 중단 + 방송 완료 확인
6. run_log 테이블에서 단계별 기록 확인
```

- [ ] **Step 3: 전체 테스트 최종 확인**

Run: `cd backend && .venv/bin/pytest && cd ../frontend && npm test`
Expected: 백엔드/프론트 모두 PASS

- [ ] **Step 4: Commit**

```bash
git add README.md backend/.env.example
git commit -m "docs: README 및 실행/E2E 절차 추가"
```

---

## 부록: 자기 검토 결과

**Spec 커버리지:**
- 데이터 모델 6테이블 → Task 1 ✓
- RRULE 반복 → Task 2, engine 재예약 ✓
- OBS 연동(씬전환/스트림키 주입/송출) → Task 3 ✓
- YouTube 연동(insert/bind/transition) → Task 4 ✓
- 실행 생명주기(go_live/시퀀스/go_complete/에러) → Task 5 ✓
- APScheduler 엔진(등록/취소/복원) → Task 6 ✓
- REST API(broadcasts/scenes/schedules) → Task 7 ✓
- YouTube 이벤트 생성/씬 동기화 → Task 8 ✓
- OAuth 인증/상태/lifespan → Task 9 ✓
- 프론트 UI 5페이지 + 시퀀스 에디터 → Task 10, 11 ✓
- TDD/테스트 전략 → 전 태스크 ✓
- 보안(.gitignore) → 이미 적용 ✓

**알려진 단순화 (수동 E2E에서 검증):**
- `live` 상태 플래그는 Task 9에서 단순화됨 → 실제 OBS is_streaming 연동은 E2E 시 보강 가능
- RTMP URL은 표준 주소 사용 (create_stream의 ingestion_url을 broadcast에 저장하는 개선은 후속)
