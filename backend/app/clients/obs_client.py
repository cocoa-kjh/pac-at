from __future__ import annotations

def _default_factory(host, port, password):
    """실제 OBS Studio 프로그램의 obs-websocket 서버와 통신하는 obsws_python 클라이언트를 생성합니다."""
    import obsws_python as obs
    return obs.ReqClient(host=host, port=port, password=password, timeout=5)


class OBSClient:
    """OBS Studio 제어 클라이언트: WebSocket 프로토콜(obsws_python)을 사용하여 OBS의 스트림 시작/중단 및 장면 전환 등을 자동화합니다."""

    def __init__(self, host: str, port: int, password: str | None, req_factory=None):
        self._host, self._port, self._password = host, port, password
        self._factory = req_factory or _default_factory
        self._req = None

    def connect(self) -> None:
        """OBS WebSocket 서버에 연결합니다."""
        if self._factory is _default_factory:
            self._req = self._factory(self._host, self._port, self._password)
        else:
            self._req = self._factory()

    def disconnect(self) -> None:
        """OBS WebSocket 연결을 해제하고 세션을 정리합니다."""
        if self._req and hasattr(self._req, "disconnect"):
            self._req.disconnect()
        self._req = None

    def list_scenes(self) -> list[str]:
        """OBS에 등록되어 있는 모든 프로그램 장면(Scene)의 이름 목록을 조회합니다."""
        resp = self._req.get_scene_list()
        return [s["sceneName"] for s in resp.scenes]

    def switch_scene(self, scene_name: str) -> None:
        """OBS의 활성 프로그램을 지정된 장면(scene_name)으로 전환합니다."""
        self._req.set_current_program_scene(scene_name)

    def set_stream_key(self, rtmp_url: str, stream_key: str) -> None:
        """OBS Studio의 스트림 대상 서버 주소(RTMP URL)와 개인 스트림 키를 동적으로 설정합니다."""
        settings = {"server": rtmp_url, "key": stream_key}
        self._req.set_stream_service_settings("rtmp_custom", settings)

    def start_stream(self) -> None:
        """OBS에서 방송 스트리밍(송출)을 시작합니다."""
        self._req.start_stream()

    def stop_stream(self) -> None:
        """OBS에서 방송 스트리밍(송출)을 중단합니다."""
        self._req.stop_stream()

    def is_streaming(self) -> bool:
        """현재 OBS가 방송을 송출하고 있는지 상태 여부를 확인합니다."""
        return bool(self._req.get_stream_status().output_active)

