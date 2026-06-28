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
