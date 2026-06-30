# Task 1 Report: SQLAlchemy データ モデル

## Summary
Task 1 completed successfully. Created SQLite data model with 6 tables using SQLAlchemy 2.0 following TDD (Test-Driven Development) methodology. All tests passing, all required files created and committed.

## Files Created
1. `backend/app/db.py` - Database engine and session factory
2. `backend/app/models.py` - SQLAlchemy ORM models (6 tables)
3. `backend/tests/conftest.py` - pytest fixtures for database testing
4. `backend/tests/test_models.py` - Integration tests for models

## TDD Process & Evidence

### Step 1: Database Module (db.py)
Created `backend/app/db.py` with:
- `Base = declarative_base()` - ORM base class
- `SessionLocal = sessionmaker(autocommit=False, autoflush=False)` - session factory
- `get_engine(db_path: str)` - returns SQLite engine
- `init_db(engine)` - initializes database and configures SessionLocal

### Step 2: Test Fixtures & Failing Tests
Created `backend/tests/conftest.py` with `db` fixture that:
- Creates in-memory SQLite database
- Creates all tables
- Configures SessionLocal
- Yields session for tests
- Cleans up after test

Created `backend/tests/test_models.py` with 2 test cases:
- `test_create_broadcast_and_schedule` - tests Broadcast and Schedule models
- `test_sequence_item_links_scene` - tests Scene and SequenceItem relationships

### Step 3: RED Phase (Failure Confirmation)

```bash
$ cd backend && .venv/bin/pytest tests/test_models.py -v
ERROR collecting tests/test_models.py
ModuleNotFoundError: No module named 'app.models'
```

**Evidence:** Tests fail with ImportError as expected because `app.models` does not exist yet.

### Step 4: Models Module (models.py)
Created `backend/app/models.py` with all 6 tables as specified:

1. **OAuthToken** (oauth_token)
   - id (Integer, PK)
   - access_token (Text)
   - refresh_token (Text)
   - expiry (DateTime)
   - scopes (Text)

2. **Scene** (scene)
   - id (Integer, PK)
   - name (String, NOT NULL)
   - obs_scene_name (String, NOT NULL)
   - note (Text, default="")

3. **Broadcast** (broadcast)
   - id (Integer, PK)
   - title (String, NOT NULL)
   - description (Text, default="")
   - privacy (String, default="private")
   - youtube_broadcast_id (String)
   - youtube_stream_key (String)
   - status (String, default="draft")
   - schedules (relationship to Schedule)

4. **Schedule** (schedule)
   - id (Integer, PK)
   - broadcast_id (Integer, FK→broadcast.id, NOT NULL)
   - start_at (DateTime, NOT NULL)
   - end_at (DateTime, NOT NULL)
   - recurrence (String, default="none")
   - recurrence_rule (Text, RRULE)
   - status (String, default="pending")
   - broadcast (relationship to Broadcast)
   - items (relationship to SequenceItem, ordered by order_index)

5. **SequenceItem** (sequence_item)
   - id (Integer, PK)
   - schedule_id (Integer, FK→schedule.id, NOT NULL)
   - scene_id (Integer, FK→scene.id, NOT NULL)
   - order_index (Integer, NOT NULL)
   - duration_seconds (Integer)
   - schedule (relationship to Schedule)
   - scene (relationship to Scene)

6. **RunLog** (run_log)
   - id (Integer, PK)
   - schedule_id (Integer, FK→schedule.id)
   - event (String, NOT NULL)
   - detail (Text, default="")
   - timestamp (DateTime, default=_utcnow)

Helper function: `_utcnow()` returns current UTC datetime for default timestamps.

### Step 5: GREEN Phase (Success Confirmation)

```bash
$ cd backend && .venv/bin/pytest tests/test_models.py -v

tests/test_models.py::test_create_broadcast_and_schedule PASSED          [ 50%]
tests/test_models.py::test_sequence_item_links_scene PASSED              [100%]

============================== 2 passed in 0.93s ===============================
```

**Evidence:** Both tests pass successfully. Models correctly:
- Create instances with specified fields
- Persist to in-memory SQLite database
- Maintain referential integrity via foreign keys
- Establish relationships (broadcast↔schedule, schedule↔items, items↔scene)

### Step 6: Git Commit

```bash
[feature/livestream-scheduler f7f69ed] feat: SQLite 데이터 모델 6개 테이블 추가
 4 files changed, 111 insertions(+)
 create mode 100644 backend/app/db.py
 create mode 100644 backend/app/models.py
 create mode 100644 backend/tests/conftest.py
 create mode 100644 backend/tests/test_models.py
```

Commit message follows the brief specification exactly.

## Verification

### Interfaces Provided (as per brief)
- ✅ `app.db.Base` - Declarative base for ORM models
- ✅ `app.db.get_engine(db_path)` - Creates SQLite engine
- ✅ `app.db.SessionLocal` - Session factory
- ✅ `app.db.init_db(engine)` - Initializes database
- ✅ `app.models.OAuthToken` - OAuth token model
- ✅ `app.models.Scene` - OBS scene model
- ✅ `app.models.Broadcast` - YouTube broadcast model
- ✅ `app.models.Schedule` - Broadcast schedule model
- ✅ `app.models.SequenceItem` - Scene sequence item model
- ✅ `app.models.RunLog` - Event logging model

### Test Coverage
- ✅ Broadcast creation and persistence
- ✅ Schedule creation with foreign key to Broadcast
- ✅ Scene creation
- ✅ SequenceItem creation with foreign keys to Schedule and Scene
- ✅ Relationship traversal (Broadcast→Schedules, Schedule→Items, Item→Scene)

## Concerns
None. All steps completed successfully, tests pass, code follows the brief specification exactly, and commit is clean.

## Next Steps
Task 1 complete. Ready for Task 2: Recurrence rule calculation phase.
