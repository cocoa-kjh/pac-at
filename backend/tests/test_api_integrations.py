import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
from app.db import Base
from app.main import app, get_db, get_youtube_dep, get_obs_dep

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

def test_sync_scenes_from_obs(client):
    c, _, obs = client
    obs.list_scenes.return_value = ["Intro", "Main"]
    r = c.post("/scenes/sync")
    assert r.status_code == 200
    names = {s["obs_scene_name"] for s in c.get("/scenes").json()}
    assert names == {"Intro", "Main"}
