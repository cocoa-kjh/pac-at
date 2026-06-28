### Task 3: OBSClient

**Files:**
- Create: `backend/app/clients/__init__.py`
- Create: `backend/app/clients/obs_client.py`
- Create: `backend/tests/test_obs_client.py`

**Interfaces:**
- Produces: `OBSClient(host, port, password)` with methods:
  - `connect() -> None`, `disconnect() -> None`
  - `list_scenes() -> list[str]`
  - `switch_scene(scene_name: str) -> None`
  - `set_stream_key(rtmp_url: str, stream_key: str) -> None`  (SetStreamServiceSettings)
  - `start_stream() -> None`, `stop_stream() -> None`
  - `is_streaming() -> bool`
- 내부적으로 `obsws-python`의 `ReqClient`를 래핑. 생성자는 `req_factory` 인자(기본 `obsws.ReqClient`)를 받아 테스트에서 모킹.

- [ ] **Step 1: 빈 `app/clients/__init__.py` 생성**

- [ ] **Step 2: 실패 테스트 작성**

```python
from unittest.mock import MagicMock
from app.clients.obs_client import OBSClient

def make_client():
    fake_req = MagicMock()
    factory = MagicMock(return_value=fake_req)
    c = OBSClient("localhost", 4455, None, req_factory=factory)
    c.connect()
    return c, fake_req

def test_list_scenes():
    c, req = make_client()
    req.get_scene_list.return_value = MagicMock(scenes=[{"sceneName": "Intro"}, {"sceneName": "Main"}])
    assert c.list_scenes() == ["Intro", "Main"]

def test_switch_scene_calls_set_program_scene():
    c, req = make_client()
    c.switch_scene("Main")
    req.set_current_program_scene.assert_called_once_with("Main")

def test_set_stream_key_calls_settings():
    c, req = make_client()
    c.set_stream_key("rtmp://a.rtmp.youtube.com/live2", "abcd-key")
    req.set_stream_service_settings.assert_called_once()

def test_start_and_stop_stream():
    c, req = make_client()
    c.start_stream(); req.start_stream.assert_called_once()
    c.stop_stream(); req.stop_stream.assert_called_once()
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && .venv/bin/pytest tests/test_obs_client.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 4: obs_client.py 구현**

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv/bin/pytest tests/test_obs_client.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/clients/__init__.py backend/app/clients/obs_client.py backend/tests/test_obs_client.py
git commit -m "feat: OBS WebSocket 클라이언트 추가"
```

---

