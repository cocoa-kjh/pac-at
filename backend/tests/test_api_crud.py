import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.main import app, get_db, get_engine_dep
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
    assert c.get("/schedules").json() == []
