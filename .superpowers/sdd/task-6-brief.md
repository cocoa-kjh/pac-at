### Task 6: 스케쥴 엔진 (APScheduler 래퍼)

**Files:**
- Create: `backend/app/scheduler/engine.py`
- Create: `backend/tests/test_engine.py`

**Interfaces:**
- Consumes: `next_occurrence`, `steps`, 모델
- Produces: `ScheduleEngine(scheduler, obs, yt, session_factory)` with:
  - `register(schedule_id: int) -> None` — DB에서 schedule 로드, start_at에 go_live 잡, end_at에 go_complete 잡, 시퀀스 중간 전환 잡 등록. 반복이면 다음 occurrence도 예약
  - `cancel(schedule_id: int) -> None` — 관련 잡 제거, status=canceled
  - `load_pending() -> None` — DB의 status=pending 스케쥴 모두 register
  - 잡 id 규칙: `f"sched:{id}:live"`, `f"sched:{id}:complete"`, `f"sched:{id}:item:{n}"`
- `scheduler`는 APScheduler `BackgroundScheduler` 인스턴스(테스트에선 MagicMock)

- [ ] **Step 1: 실패 테스트 작성**

```python
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.models import Broadcast, Schedule, Scene, SequenceItem
from app.scheduler.engine import ScheduleEngine

def _seed_two_items(db):
    b = Broadcast(title="t", privacy="private", status="scheduled",
                  youtube_broadcast_id="bc1", youtube_stream_key="k1"); db.add(b); db.commit()
    start = datetime(2026,7,1,9,tzinfo=timezone.utc)
    s = Schedule(broadcast_id=b.id, start_at=start, end_at=start+timedelta(hours=1),
                 recurrence="none", status="pending"); db.add(s); db.commit()
    sc1 = Scene(name="인트로", obs_scene_name="Intro"); db.add(sc1)
    sc2 = Scene(name="메인", obs_scene_name="Main"); db.add(sc2); db.commit()
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc1.id, order_index=0, duration_seconds=60))
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc2.id, order_index=1, duration_seconds=None))
    db.commit()
    return s

def test_register_adds_live_and_complete_jobs(db):
    from app.db import SessionLocal
    s = _seed_two_items(db)
    sched = MagicMock()
    eng = ScheduleEngine(sched, MagicMock(), MagicMock(), SessionLocal)
    eng.register(s.id)
    job_ids = [c.kwargs.get("id") or c.args[2] for c in sched.add_job.call_args_list]
    assert f"sched:{s.id}:live" in job_ids
    assert f"sched:{s.id}:complete" in job_ids
    # 두 번째 item(인트로 60초 후)에 대한 전환 잡 존재
    assert f"sched:{s.id}:item:1" in job_ids

def test_cancel_removes_jobs_and_sets_status(db):
    from app.db import SessionLocal
    s = _seed_two_items(db)
    sched = MagicMock()
    eng = ScheduleEngine(sched, MagicMock(), MagicMock(), SessionLocal)
    eng.register(s.id)
    eng.cancel(s.id)
    assert sched.remove_job.called
    db.refresh(s)
    assert s.status == "canceled"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_engine.py -v`
Expected: FAIL — `app.scheduler.engine` 없음

- [ ] **Step 3: engine.py 구현**

```python
from datetime import timedelta
from app.models import Schedule
from app.scheduler import steps
from app.scheduler.recurrence import next_occurrence

class ScheduleEngine:
    def __init__(self, scheduler, obs, yt, session_factory):
        self._sched = scheduler
        self._obs = obs
        self._yt = yt
        self._session_factory = session_factory

    def _run_go_live(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.go_live(db, self._obs, self._yt, s)
        finally:
            db.close()

    def _run_switch(self, schedule_id, index):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.switch_to_item(self._obs, s, index)
        finally:
            db.close()

    def _run_go_complete(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.go_complete(db, self._obs, self._yt, s)
            if s.recurrence_rule:
                nxt = next_occurrence(s.recurrence_rule, s.start_at)
                if nxt:
                    self._reschedule(s, nxt)
        finally:
            db.close()

    def _reschedule(self, schedule, new_start):
        duration = schedule.end_at - schedule.start_at
        schedule.start_at = new_start
        schedule.end_at = new_start + duration
        schedule.status = "pending"
        self.register(schedule.id)

    def register(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            self._sched.add_job(self._run_go_live, "date", run_date=s.start_at,
                                args=[s.id], id=f"sched:{s.id}:live",
                                replace_existing=True)
            # 시퀀스 중간 전환: order_index 0은 go_live에서 처리, 1부터 누적시간 계산
            offset = 0
            for item in s.items:
                if item.order_index == 0:
                    offset += item.duration_seconds or 0
                    continue
                run_at = s.start_at + timedelta(seconds=offset)
                self._sched.add_job(self._run_switch, "date", run_date=run_at,
                                    args=[s.id, item.order_index],
                                    id=f"sched:{s.id}:item:{item.order_index}",
                                    replace_existing=True)
                offset += item.duration_seconds or 0
            self._sched.add_job(self._run_go_complete, "date", run_date=s.end_at,
                                args=[s.id], id=f"sched:{s.id}:complete",
                                replace_existing=True)
        finally:
            db.close()

    def cancel(self, schedule_id):
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            for jid in (f"sched:{schedule_id}:live", f"sched:{schedule_id}:complete"):
                try: self._sched.remove_job(jid)
                except Exception: pass
            for item in s.items:
                try: self._sched.remove_job(f"sched:{schedule_id}:item:{item.order_index}")
                except Exception: pass
            s.status = "canceled"; db.commit()
        finally:
            db.close()

    def load_pending(self):
        db = self._session_factory()
        try:
            ids = [s.id for s in db.query(Schedule).filter(Schedule.status == "pending").all()]
        finally:
            db.close()
        for sid in ids:
            self.register(sid)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_engine.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/engine.py backend/tests/test_engine.py
git commit -m "feat: APScheduler 기반 스케쥴 실행 엔진 추가"
```

---

## Phase 5 — REST API & 인증

