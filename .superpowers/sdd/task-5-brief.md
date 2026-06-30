### Task 5: 실행 단계 함수

**Files:**
- Create: `backend/app/crud.py`
- Create: `backend/app/scheduler/steps.py`
- Create: `backend/tests/test_steps.py`

**Interfaces:**
- Consumes: `OBSClient`, `YouTubeClient`, 모델
- Produces (`app.crud`): `log_run(db, schedule_id, event, detail="") -> RunLog`, `set_broadcast_status(db, broadcast_id, status) -> None`, `set_schedule_status(db, schedule_id, status) -> None`
- Produces (`app.scheduler.steps`):
  - `go_live(db, obs, yt, schedule) -> None` — 전체 시작 시퀀스 (YouTube live 전환 → 스트림키 OBS 주입 → start_stream → 첫 씬 전환)
  - `switch_to_item(obs, schedule, index) -> None` — index번째 sequence_item 씬으로 전환
  - `go_complete(db, obs, yt, schedule) -> None` — stop_stream → YouTube complete → 상태 갱신
  - 각 함수는 예외 발생 시 `set_*_status(..., "error")` + `log_run` 후 재전파

- [ ] **Step 1: crud.py 작성**

```python
from app.models import RunLog, Broadcast, Schedule

def log_run(db, schedule_id, event, detail=""):
    entry = RunLog(schedule_id=schedule_id, event=event, detail=detail)
    db.add(entry); db.commit()
    return entry

def set_broadcast_status(db, broadcast_id, status):
    b = db.get(Broadcast, broadcast_id)
    b.status = status; db.commit()

def set_schedule_status(db, schedule_id, status):
    s = db.get(Schedule, schedule_id)
    s.status = status; db.commit()
```

- [ ] **Step 2: 실패 테스트 작성**

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.models import Broadcast, Schedule, Scene, SequenceItem
from app.scheduler import steps

def _seed(db):
    b = Broadcast(title="t", privacy="private", status="scheduled",
                  youtube_broadcast_id="bc1", youtube_stream_key="key1")
    db.add(b); db.commit()
    s = Schedule(broadcast_id=b.id,
                 start_at=datetime(2026,7,1,tzinfo=timezone.utc),
                 end_at=datetime(2026,7,1,1,tzinfo=timezone.utc),
                 recurrence="none", status="pending"); db.add(s); db.commit()
    sc = Scene(name="메인", obs_scene_name="Main"); db.add(sc); db.commit()
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc.id, order_index=0,
                        duration_seconds=None)); db.commit()
    return b, s

def test_go_live_runs_full_sequence(db):
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    s.broadcast.youtube_stream_key = "key1"
    steps.go_live(db, obs, yt, s)
    yt.transition.assert_called_with("bc1", "live")
    obs.set_stream_key.assert_called_once()
    obs.start_stream.assert_called_once()
    obs.switch_scene.assert_called_with("Main")
    db.refresh(b)
    assert b.status == "live"

def test_go_complete_stops_and_completes(db):
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    steps.go_complete(db, obs, yt, s)
    obs.stop_stream.assert_called_once()
    yt.transition.assert_called_with("bc1", "complete")
    db.refresh(b)
    assert b.status == "completed"

def test_go_live_error_sets_error_status(db):
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    obs.start_stream.side_effect = RuntimeError("OBS 연결 실패")
    try:
        steps.go_live(db, obs, yt, s)
    except RuntimeError:
        pass
    db.refresh(b)
    assert b.status == "error"
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_steps.py -v`
Expected: FAIL — `app.scheduler.steps` 없음

- [ ] **Step 4: steps.py 구현**

```python
from app import crud

# YouTube 표준 RTMP. 스트림 생성 시 받은 ingestion_url을 broadcast에 저장해
# 두는 것이 이상적이나, 본 단계에서는 broadcast.youtube_stream_key를 사용하고
# RTMP URL은 표준 주소를 사용한다.
DEFAULT_RTMP = "rtmp://a.rtmp.youtube.com/live2"

def go_live(db, obs, yt, schedule):
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_live_start")
        yt.transition(b.youtube_broadcast_id, "live")
        obs.set_stream_key(DEFAULT_RTMP, b.youtube_stream_key)
        obs.start_stream()
        switch_to_item(obs, schedule, 0)
        crud.set_broadcast_status(db, b.id, "live")
        crud.set_schedule_status(db, schedule.id, "running")
        crud.log_run(db, schedule.id, "go_live_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_live_error", str(e))
        raise

def switch_to_item(obs, schedule, index):
    items = schedule.items
    if index < 0 or index >= len(items):
        return
    obs.switch_scene(items[index].scene.obs_scene_name)

def go_complete(db, obs, yt, schedule):
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_complete_start")
        try:
            obs.stop_stream()
        finally:
            yt.transition(b.youtube_broadcast_id, "complete")
        crud.set_broadcast_status(db, b.id, "completed")
        crud.set_schedule_status(db, schedule.id, "done")
        crud.log_run(db, schedule.id, "go_complete_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_complete_error", str(e))
        raise
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_steps.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/crud.py backend/app/scheduler/steps.py backend/tests/test_steps.py
git commit -m "feat: 방송 시작/종료 실행 단계 함수 추가"
```

---

