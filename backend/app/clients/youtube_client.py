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
            "contentDetails": {"enableAutoStart": False, "enableAutoStop": False, "enableMonitorStream": False},
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

    def get_broadcast_status(self, broadcast_id: str) -> str:
        """방송의 현재 lifeCycleStatus를 반환합니다."""
        resp = self._yt.liveBroadcasts().list(
            id=broadcast_id, part="status").execute()
        return resp["items"][0]["status"]["lifeCycleStatus"]

    def get_stream_status(self, broadcast_id: str) -> str:
        """방송에 바인딩된 스트림의 streamStatus를 반환합니다."""
        resp = self._yt.liveBroadcasts().list(
            id=broadcast_id, part="contentDetails,status").execute()
        item = resp["items"][0]
        stream_id = item["contentDetails"]["boundStreamId"]
        s_resp = self._yt.liveStreams().list(
            id=stream_id, part="status").execute()
        return s_resp["items"][0]["status"]["streamStatus"]

    def wait_for_stream_active(self, broadcast_id: str, timeout: int = 60) -> None:
        """YouTube가 OBS 신호를 감지할 때까지 대기합니다 (streamStatus=active)."""
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_stream_status(broadcast_id)
            if status == "active":
                return
            time.sleep(5)
        raise TimeoutError(f"stream not active after {timeout}s (last: {status})")

    def has_monitor_stream(self, broadcast_id: str) -> bool:
        """방송의 enableMonitorStream 설정값을 반환합니다."""
        resp = self._yt.liveBroadcasts().list(
            id=broadcast_id, part="contentDetails").execute()
        return resp["items"][0]["contentDetails"].get("monitorStream", {}).get("enableMonitorStream", True)

    def wait_for_broadcast_ready(self, broadcast_id: str, timeout: int = 30) -> None:
        """broadcast lifeCycleStatus가 ready가 될 때까지 대기합니다."""
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_broadcast_status(broadcast_id)
            if status == "ready":
                return
            if status in ("live", "complete", "revoked"):
                raise RuntimeError(f"unexpected broadcast status before transition: {status}")
            time.sleep(3)
        raise TimeoutError(f"broadcast not ready after {timeout}s (last: {status})")

    def wait_for_broadcast_status(self, broadcast_id: str, target: str, timeout: int = 30) -> None:
        """broadcast lifeCycleStatus가 target이 될 때까지 대기합니다."""
        import time
        deadline = time.time() + timeout
        status = None
        while time.time() < deadline:
            status = self.get_broadcast_status(broadcast_id)
            if status == target:
                return
            time.sleep(3)
        raise TimeoutError(f"broadcast not {target} after {timeout}s (last: {status})")

    def transition(self, broadcast_id: str, status: str) -> None:
        """방송의 상태를 변경합니다."""
        self._yt.liveBroadcasts().transition(
            broadcastStatus=status, id=broadcast_id, part="id,status").execute()

    def go_live(self, broadcast_id: str) -> None:
        """enableMonitorStream 설정에 따라 올바른 경로로 live 전환합니다.

        enableMonitorStream=true : ready → testing → live
        enableMonitorStream=false: ready → live
        """
        if self.has_monitor_stream(broadcast_id):
            self.transition(broadcast_id, "testing")
            self.wait_for_broadcast_status(broadcast_id, "testing", timeout=30)
        self.transition(broadcast_id, "live")

