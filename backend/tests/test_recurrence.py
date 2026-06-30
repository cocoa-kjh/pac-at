from datetime import datetime, timezone
from app.scheduler.recurrence import next_occurrence

def test_none_rule_returns_none():
    assert next_occurrence(None, datetime(2026,7,1,tzinfo=timezone.utc)) is None
    assert next_occurrence("", datetime(2026,7,1,tzinfo=timezone.utc)) is None

def test_weekly_rule_next_monday():
    # 2026-07-01 수요일 기준, 매주 월요일 09:00 UTC
    rule = "DTSTART:20260629T090000Z\nRRULE:FREQ=WEEKLY;BYDAY=MO"
    after = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    nxt = next_occurrence(rule, after)
    assert nxt == datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)
