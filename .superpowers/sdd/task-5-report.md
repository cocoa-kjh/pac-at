# Task 5 Report: 방송 시작/종료 실행 단계 함수

## Status: COMPLETE

## Files Created
1. `/Users/cocoadev7/works/Youtube/backend/app/crud.py` - CRUD operations (log_run, set_broadcast_status, set_schedule_status)
2. `/Users/cocoadev7/works/Youtube/backend/app/scheduler/steps.py` - Execution step functions (go_live, switch_to_item, go_complete)
3. `/Users/cocoadev7/works/Youtube/backend/tests/test_steps.py` - Test suite with 3 test cases

## Test Results

### RED Phase
```
ImportError: cannot import name 'steps' from 'app.scheduler'
```
Confirmed: Tests failed because steps.py didn't exist.

### GREEN Phase
```
tests/test_steps.py::test_go_live_runs_full_sequence PASSED              [ 33%]
tests/test_steps.py::test_go_complete_stops_and_completes PASSED         [ 66%]
tests/test_steps.py::test_go_live_error_sets_error_status PASSED         [100%]

============================== 3 passed in 0.09s ===============================
```

## Commit
- SHA: `5339ab9`
- Message: `feat: 방송 시작/종료 실행 단계 함수 추가`

## Implementation Summary

### crud.py
- `log_run(db, schedule_id, event, detail="")` - Logs run events
- `set_broadcast_status(db, broadcast_id, status)` - Updates broadcast status
- `set_schedule_status(db, schedule_id, status)` - Updates schedule status

### steps.py
- `go_live(db, obs, yt, schedule)` - Executes startup: yt.transition(live) → obs.set_stream_key → obs.start_stream → switch_to_item(0) → updates status to "live"
- `switch_to_item(obs, schedule, index)` - Switches OBS scene to sequence item at index
- `go_complete(db, obs, yt, schedule)` - Executes shutdown: obs.stop_stream → yt.transition(complete) → updates status to "completed"
- All functions catch exceptions, set status to "error", log the error, and re-raise

### Tests
- `test_go_live_runs_full_sequence` - Verifies full startup sequence with correct order
- `test_go_complete_stops_and_completes` - Verifies shutdown sequence
- `test_go_live_error_sets_error_status` - Verifies error handling sets status and re-raises

## Concerns
None. All requirements met per brief. Error handling follows specification with try/except blocks, status updates, logging, and re-raising.
