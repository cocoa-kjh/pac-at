from __future__ import annotations

def _default_factory(host, port, password):
    import obsws_python as obs
    return obs.ReqClient(host=host, port=port, password=password, timeout=5)

class OBSClient:
    def __init__(self, host: str, port: int, password: str | None, req_factory=None):
        self._host, self._port, self._password = host, port, password
        self._factory = req_factory or _default_factory
        self._req = None

    def connect(self) -> None:
        if self._factory is _default_factory:
            self._req = self._factory(self._host, self._port, self._password)
        else:
            self._req = self._factory()

    def disconnect(self) -> None:
        if self._req and hasattr(self._req, "disconnect"):
            self._req.disconnect()
        self._req = None

    def list_scenes(self) -> list[str]:
        resp = self._req.get_scene_list()
        return [s["sceneName"] for s in resp.scenes]

    def switch_scene(self, scene_name: str) -> None:
        self._req.set_current_program_scene(scene_name)

    def set_stream_key(self, rtmp_url: str, stream_key: str) -> None:
        settings = {"server": rtmp_url, "key": stream_key}
        self._req.set_stream_service_settings("rtmp_custom", settings)

    def start_stream(self) -> None:
        self._req.start_stream()

    def stop_stream(self) -> None:
        self._req.stop_stream()

    def is_streaming(self) -> bool:
        return bool(self._req.get_stream_status().output_active)
