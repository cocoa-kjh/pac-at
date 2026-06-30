from datetime import datetime, timezone
from app.models import Broadcast, Schedule, Scene, SequenceItem

def test_create_broadcast_and_schedule(db):
    b = Broadcast(title="테스트", privacy="private", status="draft")
    db.add(b); db.commit()
    s = Schedule(broadcast_id=b.id,
                 start_at=datetime(2026, 7, 1, 11, tzinfo=timezone.utc),
                 end_at=datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
                 recurrence="none", status="pending")
    db.add(s); db.commit()
    assert s.id is not None
    assert s.broadcast_id == b.id

def test_sequence_item_links_scene(db):
    b = Broadcast(title="t", privacy="private", status="draft"); db.add(b); db.commit()
    s = Schedule(broadcast_id=b.id,
                 start_at=datetime(2026,7,1,tzinfo=timezone.utc),
                 end_at=datetime(2026,7,1,1,tzinfo=timezone.utc),
                 recurrence="none", status="pending"); db.add(s); db.commit()
    sc = Scene(name="인트로", obs_scene_name="Intro"); db.add(sc); db.commit()
    item = SequenceItem(schedule_id=s.id, scene_id=sc.id, order_index=0, duration_seconds=60)
    db.add(item); db.commit()
    assert item.order_index == 0
