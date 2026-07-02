from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from app.models import ScheduleSeries, ScheduleSeriesItem, Scene, Schedule
from app.scheduler.series import generate_due_occurrences


def _seed_series(db, lead_time_days=21):
    sc = Scene(name="메인", obs_scene_name="Main"); db.add(sc); db.commit()
    series = ScheduleSeries(
        first_start_at=datetime(2026, 6, 29, 9, tzinfo=timezone.utc),  # 월요일
        duration_seconds=3600,
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        title_template="{date} 정기방송",
        description_template="desc",
        privacy="private",
        lead_time_days=lead_time_days,
        active=True,
    )
    db.add(series); db.commit()
    db.add(ScheduleSeriesItem(series_id=series.id, scene_id=sc.id, order_index=0, duration_seconds=None))
    db.commit()
    return series


def _yt_mock():
    yt = MagicMock()
    yt.create_stream.return_value = ("stream1", "key-abc", "rtmp://x")
    yt.create_broadcast.side_effect = [f"bc{i}" for i in range(1, 10)]
    return yt


def test_first_occurrence_creates_stream_and_broadcast(db):
    series = _seed_series(db, lead_time_days=1)
    yt = _yt_mock()
    engine = MagicMock()
    horizon = datetime(2026, 6, 30, tzinfo=timezone.utc)  # 첫 회차만 들어오는 좁은 창

    created = generate_due_occurrences(db, yt, engine, series, horizon)

    assert len(created) == 1
    yt.create_stream.assert_called_once()
    yt.create_broadcast.assert_called_once()
    yt.bind.assert_called_once_with("bc1", "stream1")
    engine.register.assert_called_once_with(created[0].id)

    db.refresh(series)
    assert series.youtube_stream_id == "stream1"
    assert series.youtube_stream_key == "key-abc"

    sched = created[0]
    assert sched.series_id == series.id
    assert sched.broadcast.youtube_broadcast_id == "bc1"
    assert sched.broadcast.youtube_stream_key == "key-abc"
    assert sched.broadcast.title == "2026-06-29 정기방송"


def test_second_occurrence_reuses_stream_new_broadcast(db):
    series = _seed_series(db, lead_time_days=1)
    yt = _yt_mock()
    engine = MagicMock()

    generate_due_occurrences(db, yt, engine, series, datetime(2026, 6, 30, tzinfo=timezone.utc))
    created2 = generate_due_occurrences(db, yt, engine, series, datetime(2026, 7, 7, tzinfo=timezone.utc))

    assert len(created2) == 1
    # stream은 한 번만 생성 (재사용), broadcast는 두 번째도 새로 생성
    yt.create_stream.assert_called_once()
    assert yt.create_broadcast.call_count == 2
    yt.bind.assert_any_call("bc2", "stream1")

    assert db.query(Schedule).filter(Schedule.series_id == series.id).count() == 2


def test_multiple_due_occurrences_generated_in_one_call(db):
    series = _seed_series(db, lead_time_days=1)
    yt = _yt_mock()
    engine = MagicMock()
    # 3주치가 한번에 들어오는 넓은 창
    horizon = datetime(2026, 7, 14, tzinfo=timezone.utc)

    created = generate_due_occurrences(db, yt, engine, series, horizon)

    assert len(created) == 3
    assert yt.create_stream.call_count == 1
    assert yt.create_broadcast.call_count == 3


def test_generation_error_recorded_and_stops(db):
    series = _seed_series(db, lead_time_days=1)
    yt = _yt_mock()
    yt.create_broadcast.side_effect = RuntimeError("quota exceeded")
    engine = MagicMock()

    created = generate_due_occurrences(db, yt, engine, series, datetime(2026, 6, 30, tzinfo=timezone.utc))

    assert created == []
    db.refresh(series)
    assert "quota exceeded" in series.generation_error
    assert series.last_generated_start is None
