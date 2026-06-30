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

