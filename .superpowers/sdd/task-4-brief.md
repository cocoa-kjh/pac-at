### Task 4: YouTubeClient

**Files:**
- Create: `backend/app/clients/youtube_client.py`
- Create: `backend/tests/test_youtube_client.py`

**Interfaces:**
- Produces: `YouTubeClient(youtube_resource)` — 생성자는 google-api-python-client의 `build()` 결과(또는 모킹)를 주입받음. methods:
  - `create_broadcast(title, description, privacy, start_time: datetime) -> str`  (broadcast id 반환)
  - `create_stream(title: str) -> tuple[str, str, str]`  (stream_id, stream_key, ingestion_url 반환)
  - `bind(broadcast_id: str, stream_id: str) -> None`
  - `transition(broadcast_id: str, status: str) -> None`  (status: "live"|"complete"|"testing")
- Produces: `build_youtube(credentials) -> Resource` — `googleapiclient.discovery.build("youtube","v3",credentials=...)` 래퍼

- [ ] **Step 1: 실패 테스트 작성**

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.clients.youtube_client import YouTubeClient

def test_create_broadcast_returns_id():
    yt = MagicMock()
    yt.liveBroadcasts().insert().execute.return_value = {"id": "bc123"}
    client = YouTubeClient(yt)
    bid = client.create_broadcast("제목", "설명", "private",
                                  datetime(2026,7,1,tzinfo=timezone.utc))
    assert bid == "bc123"

def test_create_stream_returns_key_and_url():
    yt = MagicMock()
    yt.liveStreams().insert().execute.return_value = {
        "id": "st1",
        "cdn": {"ingestionInfo": {"streamName": "key-xyz",
                                  "ingestionAddress": "rtmp://a.rtmp.youtube.com/live2"}}}
    client = YouTubeClient(yt)
    sid, key, url = client.create_stream("내 스트림")
    assert (sid, key, url) == ("st1", "key-xyz", "rtmp://a.rtmp.youtube.com/live2")

def test_transition_calls_api():
    yt = MagicMock()
    client = YouTubeClient(yt)
    client.transition("bc123", "live")
    yt.liveBroadcasts().transition.assert_called()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_youtube_client.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: youtube_client.py 구현**

```python
from __future__ import annotations
from datetime import datetime

def build_youtube(credentials):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)

class YouTubeClient:
    def __init__(self, youtube_resource):
        self._yt = youtube_resource

    def create_broadcast(self, title: str, description: str, privacy: str,
                         start_time: datetime) -> str:
        body = {
            "snippet": {"title": title, "description": description,
                        "scheduledStartTime": start_time.isoformat()},
            "status": {"privacyStatus": privacy,
                       "selfDeclaredMadeForKids": False},
            "contentDetails": {"enableAutoStart": False, "enableAutoStop": False},
        }
        resp = self._yt.liveBroadcasts().insert(
            part="snippet,status,contentDetails", body=body).execute()
        return resp["id"]

    def create_stream(self, title: str) -> tuple[str, str, str]:
        body = {"snippet": {"title": title},
                "cdn": {"frameRate": "variable", "ingestionType": "rtmp",
                        "resolution": "variable"}}
        resp = self._yt.liveStreams().insert(
            part="snippet,cdn", body=body).execute()
        info = resp["cdn"]["ingestionInfo"]
        return resp["id"], info["streamName"], info["ingestionAddress"]

    def bind(self, broadcast_id: str, stream_id: str) -> None:
        self._yt.liveBroadcasts().bind(
            id=broadcast_id, part="id,contentDetails", streamId=stream_id).execute()

    def transition(self, broadcast_id: str, status: str) -> None:
        self._yt.liveBroadcasts().transition(
            broadcastStatus=status, id=broadcast_id, part="id,status").execute()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_youtube_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/clients/youtube_client.py backend/tests/test_youtube_client.py
git commit -m "feat: YouTube Data API 클라이언트 추가"
```

---

## Phase 4 — 실행 단계 & 엔진

