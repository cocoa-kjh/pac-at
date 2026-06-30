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
