def preflight_schedule(obs, yt, schedule):
    """스케줄 실행 전, 실제로 go_live가 성공할 수 있는 상태인지 미리 점검합니다.

    go_live를 실행하지 않고 조회만 하므로 OBS/YouTube에 부작용이 없습니다.
    """
    b = schedule.broadcast

    obs_connected = True
    live_scenes = set()
    try:
        live_scenes = set(obs.list_scenes())
    except Exception:
        obs_connected = False

    youtube_authed = yt is not None
    broadcast_ready = bool(b.youtube_broadcast_id and b.youtube_stream_key)

    problems = []
    if not obs_connected:
        problems.append("OBS에 연결되지 않음")
    if not youtube_authed:
        problems.append("YouTube 인증되지 않음")
    if not broadcast_ready:
        problems.append("방송에 YouTube 이벤트/스트림 키가 없음")

    items = schedule.items
    first_scene_ok = bool(items)
    if not items:
        problems.append("편성된 씬이 없음")

    items_report = []
    for idx, item in enumerate(items):
        role = "first" if idx == 0 else "mid"
        name = item.scene.obs_scene_name if item.scene else None
        exists = obs_connected and name is not None and name in live_scenes
        items_report.append({
            "order_index": item.order_index,
            "scene_name": name,
            "exists": exists,
            "role": role,
        })
        if role == "first" and not exists:
            first_scene_ok = False
            problems.append(f"첫 씬 '{name or '(미지정)'}' 사용 불가 — 방송 시작 시 중단됨")
        elif role == "mid" and not exists:
            problems.append(f"중간 씬 '{name or '(미지정)'}' 사용 불가 — 해당 구간은 전환 없이 건너뜀")

    ok = obs_connected and youtube_authed and broadcast_ready and first_scene_ok
    return {
        "ok": ok,
        "obs_connected": obs_connected,
        "youtube_authed": youtube_authed,
        "broadcast_ready": broadcast_ready,
        "first_scene_ok": first_scene_ok,
        "items": items_report,
        "problems": problems,
    }


def preflight_broadcast(yt, broadcast):
    """방송의 YouTube 준비 상태(이벤트 생성/스트림 키 존재)를 점검합니다."""
    youtube_authed = yt is not None
    has_event = bool(broadcast.youtube_broadcast_id)
    has_key = bool(broadcast.youtube_stream_key)

    problems = []
    if not youtube_authed:
        problems.append("YouTube 인증되지 않음")
    if not has_event:
        problems.append("YouTube 방송 이벤트가 생성되지 않음")
    if not has_key:
        problems.append("스트림 키가 없음")

    return {
        "ok": youtube_authed and has_event and has_key,
        "youtube_authed": youtube_authed,
        "has_event": has_event,
        "has_key": has_key,
        "problems": problems,
    }
