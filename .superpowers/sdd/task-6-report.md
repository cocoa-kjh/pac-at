# Task 6 Report: APScheduler 기반 스케쥴 실행 엔진

## Status: COMPLETE

## RED Evidence
`ModuleNotFoundError: No module named 'app.scheduler.engine'` — 1 error during collection.

## GREEN Evidence
`tests/test_engine.py::test_register_adds_live_and_complete_jobs PASSED`
`tests/test_engine.py::test_cancel_removes_jobs_and_sets_status PASSED`
2 passed in 0.13s

## Commit
`19d29a0` — feat: APScheduler 기반 스케쥴 실행 엔진 추가

## Full Suite
17 passed in 0.28s (all tests across 5 test files)

## Concerns
None. Implementation follows brief verbatim.

## Follow-up Fix (review)
Bug: `_reschedule`가 시각 변경 후 commit하지 않아 register()가 새 세션에서 stale 시각을 읽음.
Fix: `_reschedule(db, schedule, new_start)`에 db 인자 추가, register 전 `db.commit()`. `_run_go_complete` 호출도 `self._reschedule(db, s, nxt)`로 갱신.
Test: `test_recurrence_reschedules_after_complete` 추가 — recurrence_rule 존재 시 다음 발생(7/6)으로 전진 + register 재호출 검증. (SQLite가 tzinfo를 strip하므로 비교 전 naive→utc 보정)

Commit: `e5bef3c` — fix: 반복 스케쥴 재예약 시 시각 커밋 + 반복 경로 테스트 추가
Engine tests: 3 passed. Full suite: 18 passed.
