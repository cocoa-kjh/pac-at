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
    req.set_stream_service_settings.assert_called_once_with(
        "rtmp_custom", {"server": "rtmp://a.rtmp.youtube.com/live2", "key": "abcd-key"})

def test_start_and_stop_stream():
    c, req = make_client()
    c.start_stream(); req.start_stream.assert_called_once()
    c.stop_stream(); req.stop_stream.assert_called_once()

def test_is_streaming_reads_output_active():
    c, req = make_client()
    req.get_stream_status.return_value = MagicMock(output_active=True)
    assert c.is_streaming() is True
