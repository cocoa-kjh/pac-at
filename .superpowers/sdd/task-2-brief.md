### Task 2: RRULE 다음 발생 시각 계산

**Files:**
- Create: `backend/app/scheduler/__init__.py`
- Create: `backend/app/scheduler/recurrence.py`
- Create: `backend/tests/test_recurrence.py`

**Interfaces:**
- Produces: `next_occurrence(rrule: str | None, after: datetime) -> datetime | None` — RRULE이 None/빈문자면 None 반환, 아니면 `after` 이후 첫 발생 시각(UTC)

- [ ] **Step 1: 빈 `app/scheduler/__init__.py` 생성**

- [ ] **Step 2: 실패 테스트 작성**

```python
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
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_recurrence.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 4: recurrence.py 구현**

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_recurrence.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler/__init__.py backend/app/scheduler/recurrence.py backend/tests/test_recurrence.py
git commit -m "feat: RRULE 다음 발생 시각 계산 추가"
```

---

## Phase 3 — 외부 클라이언트

