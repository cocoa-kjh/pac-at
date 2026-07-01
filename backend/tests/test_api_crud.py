import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.main import app, get_db, get_engine_dep, get_youtube_dep
from unittest.mock import MagicMock

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
    fake_engine = MagicMock()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_engine_dep] = lambda: fake_engine
    app.dependency_overrides[get_youtube_dep] = lambda: MagicMock()
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

def test_update_broadcast_metadata(client):
    c, _ = client
    bid = c.post("/broadcasts", json={"title": "옛제목"}).json()["id"]
    r = c.patch(f"/broadcasts/{bid}", json={
        "title": "새제목", "description": "설명", "privacy": "unlisted"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "새제목"
    assert body["description"] == "설명"
    assert body["privacy"] == "unlisted"

def test_update_broadcast_partial(client):
    c, _ = client
    bid = c.post("/broadcasts", json={"title": "제목", "privacy": "private"}).json()["id"]
    r = c.patch(f"/broadcasts/{bid}", json={"description": "설명만"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "제목"          # 유지
    assert body["privacy"] == "private"     # 유지
    assert body["description"] == "설명만"

def test_update_schedule_replaces_items(client):
    c, eng = client
    bid = c.post("/broadcasts", json={"title": "b"}).json()["id"]
    sc1 = c.post("/scenes", json={"name": "a", "obs_scene_name": "A"}).json()["id"]
    sc2 = c.post("/scenes", json={"name": "b", "obs_scene_name": "B"}).json()["id"]
    sid = c.post("/schedules", json={
        "broadcast_id": bid,
        "start_at": "2026-07-01T09:00:00+00:00",
        "end_at": "2026-07-01T10:00:00+00:00",
        "items": [{"scene_id": sc1, "order_index": 0, "duration_seconds": 60}],
    }).json()["id"]
    eng.reset_mock()
    r = c.patch(f"/schedules/{sid}", json={
        "start_at": "2026-07-02T09:00:00+00:00",
        "items": [
            {"scene_id": sc2, "order_index": 0, "duration_seconds": 30},
            {"scene_id": sc1, "order_index": 1, "duration_seconds": None},
        ],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["start_at"].startswith("2026-07-02")
    assert len(body["items"]) == 2
    assert body["items"][0]["scene_id"] == sc2
    eng.reschedule_jobs.assert_called_once_with(sid)

def test_update_schedule_404(client):
    c, _ = client
    r = c.patch("/schedules/9999", json={"recurrence": "none"})
    assert r.status_code == 404

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
    assert c.get("/schedules").json() == []
