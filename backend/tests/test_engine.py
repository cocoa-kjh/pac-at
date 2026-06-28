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
