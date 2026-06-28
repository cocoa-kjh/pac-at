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
