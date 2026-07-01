import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
from app.db import Base
from app.main import app, get_db, get_youtube_dep, get_obs_dep, get_engine_dep

@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    def _get_db():
        db = TestingSessionLocal()
        try: yield db
        finally: db.close()
    yt, obs = MagicMock(), MagicMock()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_youtube_dep] = lambda: yt
    app.dependency_overrides[get_obs_dep] = lambda: obs
    app.dependency_overrides[get_engine_dep] = lambda: MagicMock()
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

def test_youtube_event_409_when_unauthed(client):
    c, yt, obs = client
    app.dependency_overrides[get_youtube_dep] = lambda: None
    bid = c.post("/broadcasts", json={"title": "방송"}).json()["id"]
    r = c.post(f"/broadcasts/{bid}/youtube")
    assert r.status_code == 409
    # restore original override
    app.dependency_overrides[get_youtube_dep] = lambda: yt

def test_update_broadcast_syncs_to_youtube(client):
    """YouTube 이벤트가 생성된 방송을 수정하면 YouTube update도 호출된다."""
    c, yt, obs = client
    yt.create_broadcast.return_value = "bc1"
    yt.create_stream.return_value = ("st1", "key1", "rtmp://x")
    bid = c.post("/broadcasts", json={"title": "옛"}).json()["id"]
    c.post(f"/broadcasts/{bid}/youtube")

    r = c.patch(f"/broadcasts/{bid}", json={"title": "새", "description": "d", "privacy": "unlisted"})
    assert r.status_code == 200
    yt.update_broadcast.assert_called_once_with("bc1", "새", "d", "unlisted")

def test_update_broadcast_no_youtube_call_when_no_event(client):
    """YouTube 이벤트가 없는 방송 수정은 update_broadcast를 호출하지 않는다."""
    c, yt, obs = client
    bid = c.post("/broadcasts", json={"title": "옛"}).json()["id"]
    r = c.patch(f"/broadcasts/{bid}", json={"title": "새"})
    assert r.status_code == 200
    yt.update_broadcast.assert_not_called()

def test_broadcast_preflight_reports_missing_stream_key(client):
    c, yt, obs = client
    bid = c.post("/broadcasts", json={"title": "방송"}).json()["id"]
    r = c.get(f"/broadcasts/{bid}/preflight")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["has_event"] is False
    assert body["has_key"] is False

def test_broadcast_preflight_ok_after_youtube_event(client):
    c, yt, obs = client
    yt.create_broadcast.return_value = "bc1"
    yt.create_stream.return_value = ("st1", "key1", "rtmp://x")
    bid = c.post("/broadcasts", json={"title": "방송"}).json()["id"]
    c.post(f"/broadcasts/{bid}/youtube")
    r = c.get(f"/broadcasts/{bid}/preflight")
    assert r.json()["ok"] is True

def test_schedule_preflight_flags_missing_first_scene(client):
    c, yt, obs = client
    yt.create_broadcast.return_value = "bc1"
    yt.create_stream.return_value = ("st1", "key1", "rtmp://x")
    bid = c.post("/broadcasts", json={"title": "방송"}).json()["id"]
    c.post(f"/broadcasts/{bid}/youtube")
    sid_scene = c.post("/scenes", json={"name": "메인", "obs_scene_name": "Main"}).json()["id"]
    sched_id = c.post("/schedules", json={
        "broadcast_id": bid,
        "start_at": "2026-07-01T09:00:00+00:00",
        "end_at": "2026-07-01T10:00:00+00:00",
        "items": [{"scene_id": sid_scene, "order_index": 0, "duration_seconds": None}],
    }).json()["id"]

    obs.list_scenes.return_value = []  # OBS에 "Main" 없음
    r = c.get(f"/schedules/{sched_id}/preflight")
    body = r.json()
    assert body["ok"] is False
    assert body["first_scene_ok"] is False
    assert any("Main" in p for p in body["problems"])

    obs.list_scenes.return_value = ["Main"]
    r = c.get(f"/schedules/{sched_id}/preflight")
    assert r.json()["ok"] is True

def test_sync_scenes_from_obs(client):
    c, _, obs = client
    obs.list_scenes.return_value = ["Intro", "Main"]
    r = c.post("/scenes/sync")
    assert r.status_code == 200
    names = {s["obs_scene_name"] for s in c.get("/scenes").json()}
    assert names == {"Intro", "Main"}

def test_sync_scenes_soft_deletes_removed_scene(client):
    """OBS에서 씬이 사라져도 sync 시 행을 삭제하지 않고 active=False로만 표시한다."""
    c, _, obs = client
    obs.list_scenes.return_value = ["Intro", "Main"]
    c.post("/scenes/sync")

    # OBS에서 "Intro" 씬 제거됨
    obs.list_scenes.return_value = ["Main"]
    r = c.post("/scenes/sync")
    assert r.status_code == 200

    scenes = {s["obs_scene_name"]: s for s in c.get("/scenes").json()}
    assert set(scenes.keys()) == {"Intro", "Main"}  # 행은 그대로 존재
    assert scenes["Intro"]["active"] is False
    assert scenes["Main"]["active"] is True

def test_sync_scenes_reactivates_returned_scene(client):
    """OBS에서 사라졌다가 다시 나타난 씬은 active=True로 복원된다."""
    c, _, obs = client
    obs.list_scenes.return_value = ["Intro"]
    c.post("/scenes/sync")
    obs.list_scenes.return_value = []
    c.post("/scenes/sync")
    obs.list_scenes.return_value = ["Intro"]
    c.post("/scenes/sync")

    scenes = {s["obs_scene_name"]: s for s in c.get("/scenes").json()}
    assert scenes["Intro"]["active"] is True
