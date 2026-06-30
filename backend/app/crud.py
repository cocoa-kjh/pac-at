from app.models import RunLog, Broadcast, Schedule


def log_run(db, schedule_id, event, detail=""):
    """Log a run event for a schedule."""
    entry = RunLog(schedule_id=schedule_id, event=event, detail=detail)
    db.add(entry)
    db.commit()
    return entry


def set_broadcast_status(db, broadcast_id, status):
    """Set the status of a broadcast."""
    b = db.get(Broadcast, broadcast_id)
    b.status = status
    db.commit()


def set_schedule_status(db, schedule_id, status):
    """Set the status of a schedule."""
    s = db.get(Schedule, schedule_id)
    s.status = status
    db.commit()
