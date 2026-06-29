from __future__ import annotations
from datetime import datetime


def build_youtube(credentials):
    """구글 OAuth 인증 정보를 사용하여 유튜브 v3 API 클라이언트 리소스를 빌드합니다."""
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


class YouTubeClient:
    """유튜브 API 클라이언트: 구글 API를 사용해 유튜브 라이브 이벤트를 예약, 생성, 연동 및 스트리밍 상태 제어(transition)를 담당합니다."""

    def __init__(self, youtube_resource):
        self._yt = youtube_resource

    def create_broadcast(self, title: str, description: str, privacy: str,
                         start_time: datetime) -> str:
        """새 유튜브 라이브 방송 이벤트(Broadcast)를 생성하고 고유의 broadcast_id를 반환합니다."""
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
        """새 라이브 스트림(RTMP 스트림 연결 정보)을 생성하여 스트림 ID, 스트림 키(Name), 스트림 서버 주소(RTMP URL)를 반환합니다."""
        body = {"snippet": {"title": title},
                "cdn": {"frameRate": "variable", "ingestionType": "rtmp",
                        "resolution": "variable"}}
        resp = self._yt.liveStreams().insert(
            part="snippet,cdn", body=body).execute()
        info = resp["cdn"]["ingestionInfo"]
        return resp["id"], info["streamName"], info["ingestionAddress"]

    def bind(self, broadcast_id: str, stream_id: str) -> None:
        """생성된 방송(broadcast_id)에 스트림 정보(stream_id)를 연동하여 방송과 송출 경로를 연결합니다."""
        self._yt.liveBroadcasts().bind(
            id=broadcast_id, part="id,contentDetails", streamId=stream_id).execute()

    def transition(self, broadcast_id: str, status: str) -> None:
        """방송의 상태를 변경합니다 (예: 'live'로 전환하여 방송 시작, 'complete'로 전환하여 방송 공식 종료)."""
        self._yt.liveBroadcasts().transition(
            broadcastStatus=status, id=broadcast_id, part="id,status").execute()

