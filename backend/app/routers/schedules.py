from fastapi import APIRouter, Depends, HTTPException
from app.main import get_db, get_engine_dep, get_obs_dep, get_youtube_dep
from app import schemas
from app.models import Schedule, SequenceItem
from app.scheduler import steps
from app.scheduler.preflight import preflight_schedule

router = APIRouter(prefix="/schedules", tags=["schedules"])

@router.post("", response_model=schemas.ScheduleOut)
def create_schedule(payload: schemas.ScheduleCreate, db=Depends(get_db),
                    engine=Depends(get_engine_dep)):
    s = Schedule(broadcast_id=payload.broadcast_id, start_at=payload.start_at,
                 end_at=payload.end_at, recurrence=payload.recurrence,
                 recurrence_rule=payload.recurrence_rule, status="pending")
    db.add(s); db.commit(); db.refresh(s)
    for item in payload.items:
        db.add(SequenceItem(schedule_id=s.id, scene_id=item.scene_id,
                            order_index=item.order_index,
                            duration_seconds=item.duration_seconds))
    db.commit()
    engine.register(s.id)
    return s

@router.get("", response_model=list[schemas.ScheduleOut])
def list_schedules(db=Depends(get_db)):
    return db.query(Schedule).all()

@router.patch("/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(schedule_id: int, payload: schemas.ScheduleUpdate,
                    db=Depends(get_db), engine=Depends(get_engine_dep)):
    """스케줄을 수정합니다.

    송출 중(running)인 스케줄은 수정을 거부합니다. items가 주어지면 기존 시퀀스를
    전부 교체합니다. 종료/오류/취소 상태였다면 재실행 대상으로 pending 복원 후
    엔진 job을 재등록합니다.
    """
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(404, "schedule not found")
    if s.status == "running":
        raise HTTPException(409, "송출 중인 스케줄은 수정할 수 없음")

    data = payload.model_dump(exclude_unset=True)
    for field in ("broadcast_id", "start_at", "end_at", "recurrence", "recurrence_rule"):
        if field in data and data[field] is not None:
            setattr(s, field, data[field])

    if "items" in data and data["items"] is not None:
        db.query(SequenceItem).filter(SequenceItem.schedule_id == s.id).delete()
        for item in payload.items:
            db.add(SequenceItem(schedule_id=s.id, scene_id=item.scene_id,
                                order_index=item.order_index,
                                duration_seconds=item.duration_seconds))

    # 실행 종료/오류/취소 상태였으면 재실행 대상으로 복원
    if s.status in ("done", "error", "canceled"):
        s.status = "pending"

    db.commit(); db.refresh(s)
    engine.reschedule_jobs(s.id)
    return s


@router.get("/{schedule_id}/preflight")
def schedule_preflight(schedule_id: int, db=Depends(get_db),
                       obs=Depends(get_obs_dep), yt=Depends(get_youtube_dep)):
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(404, "schedule not found")
    return preflight_schedule(obs, yt, s)

@router.post("/{schedule_id}/go-live")
def manual_go_live(schedule_id: int, db=Depends(get_db),
                   obs=Depends(get_obs_dep), yt=Depends(get_youtube_dep)):
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(404, "schedule not found")
    if s.status not in ("pending", "error"):
        raise HTTPException(409, f"schedule status is '{s.status}', expected pending or error")
    if yt is None:
        raise HTTPException(409, "youtube not authenticated")
    steps.go_live(db, obs, yt, s)
    return {"ok": True}

@router.post("/{schedule_id}/go-complete")
def manual_go_complete(schedule_id: int, db=Depends(get_db),
                       obs=Depends(get_obs_dep), yt=Depends(get_youtube_dep)):
    s = db.get(Schedule, schedule_id)
    if not s:
        raise HTTPException(404, "schedule not found")
    if s.status != "running":
        raise HTTPException(409, f"schedule status is '{s.status}', expected running")
    if yt is None:
        raise HTTPException(409, "youtube not authenticated")
    steps.go_complete(db, obs, yt, s)
    return {"ok": True}

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db=Depends(get_db),
                    engine=Depends(get_engine_dep)):
    s = db.get(Schedule, schedule_id)
    if not s: raise HTTPException(404)
    engine.cancel(schedule_id)
    db.delete(s)
    db.commit()
    return {"ok": True}
