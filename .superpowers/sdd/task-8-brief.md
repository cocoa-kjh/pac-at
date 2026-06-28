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

