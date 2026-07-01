import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.models import Broadcast, Schedule, Scene, SequenceItem
from app.scheduler import steps
from app.exceptions import SceneError


def _seed(db):
    """Create test data: broadcast, schedule, scene, and sequence item."""
    b = Broadcast(
        title="t",
        privacy="private",
        status="scheduled",
        youtube_broadcast_id="bc1",
        youtube_stream_key="key1"
    )
    db.add(b)
    db.commit()

    s = Schedule(
        broadcast_id=b.id,
        start_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 1, 1, tzinfo=timezone.utc),
        recurrence="none",
        status="pending"
    )
    db.add(s)
    db.commit()

    sc = Scene(name="메인", obs_scene_name="Main")
    db.add(sc)
    db.commit()

    db.add(SequenceItem(
        schedule_id=s.id,
        scene_id=sc.id,
        order_index=0,
        duration_seconds=None
    ))
    db.commit()

    return b, s


def test_go_live_runs_full_sequence(db):
    """Test that go_live runs the full startup sequence in correct order."""
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    s.broadcast.youtube_stream_key = "key1"
    obs.is_streaming.return_value = False
    obs.list_scenes.return_value = ["Main"]

    steps.go_live(db, obs, yt, s)

    yt.go_live.assert_called_with("bc1")
    obs.set_stream_key.assert_called_once()
    obs.start_stream.assert_called_once()
    obs.switch_scene.assert_called_with("Main")

    db.refresh(b)
    assert b.status == "live"


def test_go_live_aborts_when_first_scene_missing_in_obs(db):
    """OBS에 첫 씬이 없으면 송출을 시작하지 않고 SceneError로 중단한다."""
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    obs.list_scenes.return_value = []  # 첫 씬 "Main"이 OBS에 없음

    with pytest.raises(SceneError):
        steps.go_live(db, obs, yt, s)

    obs.start_stream.assert_not_called()
    yt.go_live.assert_not_called()
    db.refresh(b)
    assert b.status == "error"


def test_go_live_aborts_when_no_items(db):
    """편성된 씬이 없으면 송출을 시작하지 않고 SceneError로 중단한다."""
    b, s = _seed(db)
    for item in list(s.items):
        db.delete(item)
    db.commit()
    db.refresh(s)
    obs, yt = MagicMock(), MagicMock()

    with pytest.raises(SceneError):
        steps.go_live(db, obs, yt, s)

    obs.start_stream.assert_not_called()


def test_switch_to_item_skips_missing_mid_scene(db):
    """중간 씬이 OBS에 없으면 방송을 중단하지 않고 전환만 건너뛴다."""
    b, s = _seed(db)
    sc2 = Scene(name="서브", obs_scene_name="Sub")
    db.add(sc2); db.commit()
    db.add(SequenceItem(schedule_id=s.id, scene_id=sc2.id, order_index=1, duration_seconds=60))
    db.commit(); db.refresh(s)

    obs = MagicMock()
    obs.list_scenes.return_value = ["Main"]  # "Sub"는 OBS에 없음

    steps.switch_to_item(obs, s, 1, db=db)

    obs.switch_scene.assert_not_called()


def test_go_complete_stops_and_completes(db):
    """Test that go_complete stops the stream and transitions to complete."""
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()

    steps.go_complete(db, obs, yt, s)

    obs.stop_stream.assert_called_once()
    yt.transition.assert_called_with("bc1", "complete")

    db.refresh(b)
    assert b.status == "completed"


def test_go_live_error_sets_error_status(db):
    """Test that go_live sets error status and re-raises on exception."""
    b, s = _seed(db)
    obs, yt = MagicMock(), MagicMock()
    obs.list_scenes.return_value = ["Main"]
    obs.start_stream.side_effect = RuntimeError("OBS 연결 실패")

    try:
        steps.go_live(db, obs, yt, s)
    except RuntimeError:
        pass

    db.refresh(b)
    assert b.status == "error"
