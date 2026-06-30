from app import crud

# YouTube standard RTMP. Stream creation returns an ingestion_url that should
# ideally be stored in broadcast, but in this stage we use broadcast.youtube_stream_key
# and the standard YouTube RTMP URL.
DEFAULT_RTMP = "rtmp://a.rtmp.youtube.com/live2"


def go_live(db, obs, yt, schedule):
    """Execute the full startup sequence for a live broadcast.

    Order:
    1. YouTube transition to live
    2. Set stream key in OBS
    3. Start OBS stream
    4. Switch to first scene
    5. Update broadcast and schedule status

    On exception, sets broadcast status to 'error', logs, and re-raises.
    """
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_live_start")
        yt.transition(b.youtube_broadcast_id, "live")
        obs.set_stream_key(DEFAULT_RTMP, b.youtube_stream_key)
        obs.start_stream()
        switch_to_item(obs, schedule, 0)
        crud.set_broadcast_status(db, b.id, "live")
        crud.set_schedule_status(db, schedule.id, "running")
        crud.log_run(db, schedule.id, "go_live_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_live_error", str(e))
        raise


def switch_to_item(obs, schedule, index):
    """Switch OBS scene to the scene of the sequence item at the given index.

    Silently returns if index is out of bounds.
    """
    items = schedule.items
    if index < 0 or index >= len(items):
        return
    obs.switch_scene(items[index].scene.obs_scene_name)


def go_complete(db, obs, yt, schedule):
    """Execute the complete sequence for ending a live broadcast.

    Order:
    1. Stop OBS stream (with finally block to ensure YouTube transition happens)
    2. YouTube transition to complete
    3. Update broadcast and schedule status

    On exception, sets broadcast status to 'error', logs, and re-raises.
    """
    b = schedule.broadcast
    try:
        crud.log_run(db, schedule.id, "go_complete_start")
        try:
            obs.stop_stream()
        finally:
            yt.transition(b.youtube_broadcast_id, "complete")
        crud.set_broadcast_status(db, b.id, "completed")
        crud.set_schedule_status(db, schedule.id, "done")
        crud.log_run(db, schedule.id, "go_complete_done")
    except Exception as e:
        crud.set_broadcast_status(db, b.id, "error")
        crud.log_run(db, schedule.id, "go_complete_error", str(e))
        raise
