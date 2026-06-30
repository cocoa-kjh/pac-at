from fastapi import APIRouter, Depends, HTTPException
from app.main import get_db, get_engine_dep
from app import schemas
from app.models import Schedule, SequenceItem

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

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db=Depends(get_db),
                    engine=Depends(get_engine_dep)):
    s = db.get(Schedule, schedule_id)
    if not s: raise HTTPException(404)
    engine.cancel(schedule_id)
    db.delete(s)
    db.commit()
    return {"ok": True}
