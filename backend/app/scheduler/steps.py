from app import crud

# YouTube 표준 RTMP 스트림 서버 주소
# 스트림 생성 시 고유의 ingestion_url을 제공받지만, 여기서는 표준 유튜브 RTMP URL과 방송의 stream_key 조합을 사용합니다.
DEFAULT_RTMP = "rtmp://a.rtmp.youtube.com/live2"


def go_live(db, obs, yt, schedule):
    """실시간 방송의 전체 시작 시퀀스를 처리합니다.

    실행 순서:
    1. YouTube 방송 상태를 'live'(실시간)로 전환
    2. OBS의 스트림 키 설정
    3. OBS 방송 시작 (송출 개시)
    4. 첫 번째 장면(index=0)으로 전환
    5. DB 내 방송 및 스케줄 상태 업데이트 ('live', 'running')

    오류가 발생하면 방송 상태를 'error'로 설정하고 로그를 남긴 후 예외를 다시 던집니다.
    """
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_live_start")
        
        # OBS가 이미 송출 중인 경우, 새로운 스트림 키 설정을 적용하기 위해 먼저 송출을 중단합니다.
        if obs.is_streaming():
            crud.log_run(db, schedule.id, "go_live_info", "OBS is already streaming. Stopping it to apply new stream key.")
            obs.stop_stream()
            import time
            for _ in range(10):  # 최대 5초 동안 완전히 멈출 때까지 대기
                if not obs.is_streaming():
                    break
                time.sleep(0.5)

        obs.set_stream_key(DEFAULT_RTMP, b.youtube_stream_key)
        obs.start_stream()
        yt.wait_for_stream_active(b.youtube_broadcast_id, timeout=60)
        yt.wait_for_broadcast_ready(b.youtube_broadcast_id, timeout=30)
        yt.go_live(b.youtube_broadcast_id)
        switch_to_item(obs, schedule, 0)
        crud.set_broadcast_status(db, b.id, "live")
        crud.set_schedule_status(db, schedule.id, "running")
        crud.log_run(db, schedule.id, "go_live_done")

    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_live_error", str(e))
        raise


def switch_to_item(obs, schedule, index):
    """OBS 장면을 현재 스케줄의 특정 순서(index)에 정의된 OBS 장면 명으로 전환합니다.

    인덱스가 유효 범위를 벗어나면 아무것도 하지 않고 무시합니다.
    """
    items = schedule.items
    if index < 0 or index >= len(items):
        return
    obs.switch_scene(items[index].scene.obs_scene_name)


def go_complete(db, obs, yt, schedule):
    """실시간 방송의 전체 종료 시퀀스를 처리합니다.

    실행 순서:
    1. OBS 방송 중단 (YouTube 상태 전환을 보장하기 위해 try/finally 사용)
    2. YouTube 방송 상태를 'complete'(종료)로 전환
    3. DB 내 방송 및 스케줄 상태 업데이트 ('completed', 'done')

    오류가 발생하면 방송 상태를 'error'로 설정하고 로그를 남긴 후 예외를 다시 던집니다.
    """
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_complete_start")
        try:
            obs.stop_stream()
        finally:
            # OBS 송출 중단 실패 여부와 상관없이 유튜브 스트림은 반드시 complete 상태로 닫아줍니다.
            yt.transition(b.youtube_broadcast_id, "complete")
        crud.set_broadcast_status(db, b.id, "completed")
        crud.set_schedule_status(db, schedule.id, "done")
        crud.log_run(db, schedule.id, "go_complete_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_complete_error", str(e))
        raise

