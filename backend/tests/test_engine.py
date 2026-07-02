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

def test_go_complete_does_not_reschedule_same_schedule(db):
    """반복은 이제 ScheduleSeries가 담당 — go_complete은 해당 회차 종료만 하고
    start_at을 건드리거나 재등록하지 않는다."""
    from app.db import SessionLocal
    b = Broadcast(title="t", privacy="private", status="live",
                  youtube_broadcast_id="bc1", youtube_stream_key="k1"); db.add(b); db.commit()
    start = datetime(2026,6,29,9,tzinfo=timezone.utc)
    s = Schedule(broadcast_id=b.id, start_at=start, end_at=start+timedelta(hours=1),
                 recurrence="none", status="running"); db.add(s); db.commit()
    sched = MagicMock()
    eng = ScheduleEngine(sched, MagicMock(), MagicMock(), SessionLocal)
    eng._run_go_complete(s.id)
    db.refresh(s)
    got = s.start_at.replace(tzinfo=timezone.utc) if s.start_at.tzinfo is None else s.start_at
    assert got == start
    assert s.status == "done"
    sched.add_job.assert_not_called()

def test_reschedule_jobs_removes_old_and_reregisters_without_canceling(db):
    from app.db import SessionLocal
    s = _seed_two_items(db)
    sched = MagicMock()
    # 스케줄러에 기존 job이 등록돼 있다고 가정 (item:1, item:2 등 orphan 포함)
    jobs = []
    for jid in [f"sched:{s.id}:live", f"sched:{s.id}:complete",
                f"sched:{s.id}:item:1", f"sched:{s.id}:item:2"]:
        j = MagicMock(); j.id = jid; jobs.append(j)
    sched.get_jobs.return_value = jobs
    eng = ScheduleEngine(sched, MagicMock(), MagicMock(), SessionLocal)

    eng.reschedule_jobs(s.id)

    # orphan 포함 모든 기존 job 제거됨
    removed = {c.args[0] for c in sched.remove_job.call_args_list}
    assert f"sched:{s.id}:item:2" in removed  # 줄어든 orphan도 제거
    assert f"sched:{s.id}:live" in removed
    # 재등록됨
    job_ids = [c.kwargs.get("id") or c.args[2] for c in sched.add_job.call_args_list]
    assert f"sched:{s.id}:live" in job_ids
    # status는 건드리지 않음
    db.refresh(s)
    assert s.status == "pending"

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
