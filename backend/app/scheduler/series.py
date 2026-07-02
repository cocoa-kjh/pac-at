from datetime import timedelta, timezone
from app.models import Broadcast, Schedule, SequenceItem, ScheduleSeries
from app.scheduler.recurrence import next_occurrence


def _render(template: str, start_at) -> str:
    return template.replace("{date}", start_at.strftime("%Y-%m-%d"))


def _full_rrule(series: ScheduleSeries) -> str:
    """series.recurrence_rule(순수 RRULE)에 first_start_at을 DTSTART로 붙여
    dateutil이 요일/시각을 정확히 계산하도록 만든다."""
    anchor = series.first_start_at
    return f"DTSTART:{anchor.strftime('%Y%m%dT%H%M%SZ')}\nRRULE:{series.recurrence_rule}"


def _compute_next_start(series: ScheduleSeries):
    if series.last_generated_start is None:
        return series.first_start_at
    return next_occurrence(_full_rrule(series), series.last_generated_start)


def _create_occurrence(db, yt, engine, series: ScheduleSeries, start_at):
    """회차 하나를 실제로 생성한다: Broadcast(신규) + YouTube 이벤트(신규, 기존 stream에 bind)
    + Schedule/SequenceItem(신규) + 엔진 등록."""
    end_at = start_at + timedelta(seconds=series.duration_seconds)
    title = _render(series.title_template, start_at)

    b = Broadcast(title=title, description=series.description_template,
                  privacy=series.privacy, status="draft")
    db.add(b)
    db.commit()
    db.refresh(b)

    if series.youtube_stream_id is None:
        # 시리즈 최초 회차: stream(송출 경로)을 한 번만 생성해 이후 계속 재사용
        stream_id, key, _url = yt.create_stream(f"{series.title_template} stream")
        series.youtube_stream_id = stream_id
        series.youtube_stream_key = key
        db.commit()

    bid = yt.create_broadcast(title, series.description_template, series.privacy, start_at)
    yt.bind(bid, series.youtube_stream_id)

    b.youtube_broadcast_id = bid
    b.youtube_stream_key = series.youtube_stream_key
    b.status = "scheduled"
    db.commit()

    s = Schedule(broadcast_id=b.id, series_id=series.id, start_at=start_at, end_at=end_at,
                 recurrence="none", status="pending")
    db.add(s)
    db.commit()
    db.refresh(s)

    for it in series.items:
        db.add(SequenceItem(schedule_id=s.id, scene_id=it.scene_id,
                            order_index=it.order_index, duration_seconds=it.duration_seconds))
    db.commit()

    engine.register(s.id)
    return s


def generate_due_occurrences(db, yt, engine, series: ScheduleSeries, horizon):
    """series.lead_time_days 내에 들어오는 회차를 모두 생성한다 (여러 회차가 밀려있으면 순서대로).

    YouTube 이벤트 생성 중 오류가 나면 series.generation_error에 기록하고 중단한다
    (다음 주기 실행 때 같은 지점부터 재시도).
    """
    created = []
    while True:
        nxt = _compute_next_start(series)
        if nxt is None:
            break
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        if nxt > horizon:
            break
        try:
            sched = _create_occurrence(db, yt, engine, series, nxt)
            created.append(sched)
            series.last_generated_start = nxt
            series.generation_error = None
            db.commit()
        except Exception as e:
            series.generation_error = str(e)
            db.commit()
            break
    return created


def generate_all_pending(db, yt, engine):
    """모든 활성 시리즈에 대해 lead_time 내 회차를 생성한다. 주기적으로 호출되는 진입점."""
    from datetime import datetime
    if yt is None:
        return
    now = datetime.now(timezone.utc)
    for series in db.query(ScheduleSeries).filter(ScheduleSeries.active.is_(True)).all():
        horizon = now + timedelta(days=series.lead_time_days)
        generate_due_occurrences(db, yt, engine, series, horizon)
