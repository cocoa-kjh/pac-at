from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.models import Broadcast, Schedule, Scene, SequenceItem
from app.scheduler import steps


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

    steps.go_live(db, obs, yt, s)

    yt.go_live.assert_called_with("bc1")
    obs.set_stream_key.assert_called_once()
    obs.start_stream.assert_called_once()
    obs.switch_scene.assert_called_with("Main")

    db.refresh(b)
    assert b.status == "live"


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
    obs.start_stream.side_effect = RuntimeError("OBS 연결 실패")

    try:
        steps.go_live(db, obs, yt, s)
    except RuntimeError:
        pass

    db.refresh(b)
    assert b.status == "error"
