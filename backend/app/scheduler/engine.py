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
                    self._reschedule(db, s, nxt)
        finally:
            db.close()

    def _reschedule(self, db, schedule, new_start):
        duration = schedule.end_at - schedule.start_at
        schedule.start_at = new_start
        schedule.end_at = new_start + duration
        schedule.status = "pending"
        db.commit()
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
                try:
                    self._sched.remove_job(jid)
                except Exception:
                    pass
            for item in s.items:
                try:
                    self._sched.remove_job(f"sched:{schedule_id}:item:{item.order_index}")
                except Exception:
                    pass
            s.status = "canceled"
            db.commit()
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
