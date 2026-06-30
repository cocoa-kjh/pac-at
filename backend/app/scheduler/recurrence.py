from datetime import datetime, timezone
from dateutil import rrule as _rrule

def next_occurrence(rrule: str | None, after: datetime) -> datetime | None:
    if not rrule:
        return None
    if after.tzinfo is None:
        after = after.replace(tzinfo=timezone.utc)
    rs = _rrule.rrulestr(rrule, forceset=True)
    nxt = rs.after(after, inc=False)
    if nxt is None:
        return None
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=timezone.utc)
    return nxt.astimezone(timezone.utc)
