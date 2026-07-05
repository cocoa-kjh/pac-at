import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.main import app, get_db, get_obs_dep

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

def test_status_live_false_when_no_live_broadcast(client):
    c, _ = client
    assert c.get("/status").json()["live"] is False

def test_status_live_true_when_broadcast_is_live(client):
    from app.models import Broadcast
    from app.main import get_db
    c, _ = client
    db = next(app.dependency_overrides[get_db]())
    db.add(Broadcast(title="t", privacy="private", status="live"))
    db.commit()
    assert c.get("/status").json()["live"] is True

def test_status_reconnects_obs_when_initially_disconnected(client):
    c, obs = client
    obs.is_streaming.side_effect = [Exception("no conn"), True]
    r = c.get("/status")
    assert r.json()["obs_connected"] is True
    obs.connect.assert_called_once()
