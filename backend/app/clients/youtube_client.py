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
