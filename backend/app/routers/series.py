from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.main import get_db, get_youtube_dep, get_engine_dep
from app import schemas
from app.models import ScheduleSeries, ScheduleSeriesItem, Schedule
from app.scheduler.series import generate_due_occurrences

router = APIRouter(prefix="/series", tags=["series"])


@router.post("", response_model=schemas.SeriesOut)
def create_series(payload: schemas.SeriesCreate, db=Depends(get_db),
                  yt=Depends(get_youtube_dep), engine=Depends(get_engine_dep)):
    """반복 시리즈를 생성하고, lead_time_days 이내에 들어오는 첫 회차(들)를 즉시 생성한다."""
    if yt is None:
        raise HTTPException(409, "YouTube not authenticated")
    series = ScheduleSeries(
        first_start_at=payload.first_start_at,
        duration_seconds=payload.duration_seconds,
        recurrence_rule=payload.recurrence_rule,
        title_template=payload.title_template,
        description_template=payload.description_template,
        privacy=payload.privacy,
        lead_time_days=payload.lead_time_days,
        active=True,
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    for item in payload.items:
        db.add(ScheduleSeriesItem(series_id=series.id, scene_id=item.scene_id,
                                  order_index=item.order_index,
                                  duration_seconds=item.duration_seconds))
    db.commit()

    horizon = datetime.now(timezone.utc) + timedelta(days=series.lead_time_days)
    generate_due_occurrences(db, yt, engine, series, horizon)
    db.refresh(series)
    return series


@router.get("", response_model=list[schemas.SeriesOut])
def list_series(db=Depends(get_db)):
    return db.query(ScheduleSeries).all()


@router.patch("/{series_id}", response_model=schemas.SeriesOut)
def update_series(series_id: int, payload: schemas.SeriesUpdate, db=Depends(get_db)):
    """시리즈 템플릿을 수정한다. 이미 생성된 회차(Schedule)에는 영향 없음 — 이후 새로 생성되는 회차부터 적용."""
    series = db.get(ScheduleSeries, series_id)
    if not series:
        raise HTTPException(404, "series not found")

    data = payload.model_dump(exclude_unset=True)
    for field in ("recurrence_rule", "duration_seconds", "title_template",
                  "description_template", "privacy", "lead_time_days", "active"):
        if field in data and data[field] is not None:
            setattr(series, field, data[field])

    if "items" in data and data["items"] is not None:
        db.query(ScheduleSeriesItem).filter(ScheduleSeriesItem.series_id == series.id).delete()
        for item in payload.items:
            db.add(ScheduleSeriesItem(series_id=series.id, scene_id=item.scene_id,
                                      order_index=item.order_index,
                                      duration_seconds=item.duration_seconds))

    db.commit()
    db.refresh(series)
    return series


@router.delete("/{series_id}")
def delete_series(series_id: int, db=Depends(get_db)):
    """향후 회차 생성을 중단한다 (active=False). 이미 생성된 회차는 그대로 유지되며
    필요하면 /schedules/{id} DELETE로 개별 취소한다."""
    series = db.get(ScheduleSeries, series_id)
    if not series:
        raise HTTPException(404, "series not found")
    series.active = False
    db.commit()
    return {"ok": True}


@router.get("/{series_id}/occurrences", response_model=list[schemas.ScheduleOut])
def list_occurrences(series_id: int, db=Depends(get_db)):
    return db.query(Schedule).filter(Schedule.series_id == series_id).all()
