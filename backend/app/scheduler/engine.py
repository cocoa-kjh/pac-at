from datetime import timedelta, timezone
from app.models import Schedule
from app.scheduler import steps


class ScheduleEngine:
    """스케줄링 엔진: APScheduler를 래핑하여 방송 시작/장면 전환/방송 종료 작업을 예약 관리하고 자동 반복(RRULE)을 처리합니다."""

    def __init__(self, scheduler, obs, yt, session_factory):
        self._sched = scheduler
        self._obs = obs
        self._yt = yt
        self._session_factory = session_factory

    def _run_go_live(self, schedule_id):
        """예약 시간에 맞춰 실시간 방송 송출 및 첫 장면 전환을 처리합니다."""
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.go_live(db, self._obs, self._yt, s)
        finally:
            db.close()

    def _run_switch(self, schedule_id, index):
        """지정된 순서(index)에 맞춰 OBS 장면을 자동으로 전환합니다."""
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.switch_to_item(self._obs, s, index, db=db)
        finally:
            db.close()

    def _run_go_complete(self, schedule_id):
        """방송을 종료하고 송출을 중단합니다.

        반복 방송은 ScheduleSeries가 담당(app/scheduler/series.py) — 회차마다 새
        Broadcast/Schedule을 미리 생성해두므로, 여기서는 해당 회차 종료 처리만 한다.
        """
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            steps.go_complete(db, self._obs, self._yt, s)
        finally:
            db.close()

    def register(self, schedule_id):
        """주어진 스케줄 ID에 해당하는 방송 시작, 순차 장면 전환, 방송 종료 작업을 스케줄러(APScheduler)에 등록합니다."""
        db = self._session_factory()
        try:
            s = db.get(Schedule, schedule_id)
            
            # SQLite에서 읽어온 naive datetime을 UTC timezone-aware datetime으로 변환
            start_at = s.start_at
            if start_at.tzinfo is None:
                start_at = start_at.replace(tzinfo=timezone.utc)
            end_at = s.end_at
            if end_at.tzinfo is None:
                end_at = end_at.replace(tzinfo=timezone.utc)

            # 1. 방송 시작 예약 (Start At)
            self._sched.add_job(self._run_go_live, "date", run_date=start_at,
                                args=[s.id], id=f"sched:{s.id}:live",
                                replace_existing=True, misfire_grace_time=300)
            
            # 2. 시퀀스 중간 장면 전환 예약: order_index 0은 go_live에서 즉시 처리, 1부터 누적시간에 맞춰 예약
            offset = 0
            for item in s.items:
                if item.order_index == 0:
                    offset += item.duration_seconds or 0
                    continue
                run_at = start_at + timedelta(seconds=offset)
                self._sched.add_job(self._run_switch, "date", run_date=run_at,
                                    args=[s.id, item.order_index],
                                    id=f"sched:{s.id}:item:{item.order_index}",
                                    replace_existing=True)
                offset += item.duration_seconds or 0
            
            # 3. 방송 종료 예약 (End At)
            self._sched.add_job(self._run_go_complete, "date", run_date=end_at,
                                args=[s.id], id=f"sched:{s.id}:complete",
                                replace_existing=True, misfire_grace_time=300)
        finally:
            db.close()

    def _remove_all_jobs(self, schedule_id):
        """해당 스케줄의 시작/종료/모든 장면전환 job을 제거합니다 (상태 변경 없음).

        시퀀스 item 개수가 줄어든 경우에도 orphan 전환 job이 남지 않도록,
        DB의 현재 item이 아니라 스케줄러에 실제 등록된 job id를 prefix로 스캔해
        제거합니다.
        """
        prefix = f"sched:{schedule_id}:"
        for job in self._sched.get_jobs():
            if job.id and job.id.startswith(prefix):
                try:
                    self._sched.remove_job(job.id)
                except Exception:
                    pass

    def reschedule_jobs(self, schedule_id):
        """스케줄 수정 후 호출: 기존 job을 모두 제거하고 현재 DB 상태로 재등록합니다.

        cancel과 달리 status를 'canceled'로 바꾸지 않습니다.
        """
        self._remove_all_jobs(schedule_id)
        self.register(schedule_id)

    def cancel(self, schedule_id):
        """스케줄러에 등록되어 있던 해당 스케줄의 모든 작업(시작/전환/종료)을 취소하고 상태를 복원합니다."""
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
        """서버가 시작될 때 DB에서 대기 상태('pending')인 모든 스케줄을 스케줄러에 다시 등록합니다."""
        db = self._session_factory()
        try:
            ids = [s.id for s in db.query(Schedule).filter(Schedule.status == "pending").all()]
        finally:
            db.close()
        for sid in ids:
            self.register(sid)

