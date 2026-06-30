
## Final Fix Results (2026-06-28)

- **Commit**: `2b2af48` — fix: YouTube 미인증 409 가드 및 인증 후 클라이언트 재빌드, 스케쥴 하드삭제, .env 로드
- **Full suite**: 26 passed (was 25), 0 failures, 4 deprecation warnings (Pydantic v2 schema style — pre-existing, not introduced here)
- **Fix 1**: broadcasts.py guards `yt is None` → 409; auth.py rebuilds `app.state.youtube` after callback commit; new test `test_youtube_event_409_when_unauthed` added
- **Fix 2**: schedules.py `delete_schedule` now calls `db.delete(s); db.commit()` after `engine.cancel`; existing test extended to assert GET /schedules returns `[]`
- **Fix 3**: `python-dotenv>=1.0` added to pyproject.toml; `config.py` calls `load_dotenv()` before env reads
