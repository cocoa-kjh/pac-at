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

