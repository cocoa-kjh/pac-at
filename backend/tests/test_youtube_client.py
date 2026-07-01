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
    yt.liveBroadcasts().transition.assert_called_with(
        broadcastStatus="live", id="bc123", part="id,status")


def test_update_broadcast_preserves_existing_snippet():
    yt = MagicMock()
    # 기존 snippet에 scheduledStartTime 등 보존해야 할 값이 있음
    yt.liveBroadcasts().list().execute.return_value = {
        "items": [{
            "snippet": {"title": "옛제목", "description": "옛설명",
                        "scheduledStartTime": "2026-07-01T09:00:00Z"},
            "status": {"privacyStatus": "private"},
        }]
    }
    client = YouTubeClient(yt)
    client.update_broadcast("bc123", "새제목", "새설명", "unlisted")

    _, kwargs = yt.liveBroadcasts().update.call_args
    body = kwargs["body"]
    assert body["id"] == "bc123"
    assert body["snippet"]["title"] == "새제목"
    assert body["snippet"]["description"] == "새설명"
    assert body["snippet"]["scheduledStartTime"] == "2026-07-01T09:00:00Z"  # 보존
    assert body["status"]["privacyStatus"] == "unlisted"
