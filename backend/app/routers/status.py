from fastapi import APIRouter, Depends
from app.main import get_db, get_obs_dep
from app.models import OAuthToken, Schedule, Broadcast

router = APIRouter(tags=["status"])

@router.get("/status")
def status(db=Depends(get_db), obs=Depends(get_obs_dep)):
    token = db.query(OAuthToken).first()
    nxt = (db.query(Schedule)
             .filter(Schedule.status == "pending")
             .order_by(Schedule.start_at).first())
    live = db.query(Broadcast).filter(Broadcast.status == "live").first() is not None

    try:
        obs.is_streaming()
        obs_connected = True
    except Exception:
        # 최초 연결 실패 후 OBS를 나중에 켠 경우를 위해 요청마다 재연결 시도
        try:
            obs.connect()
            obs.is_streaming()
            obs_connected = True
        except Exception:
            obs_connected = False

    return {
        "obs_connected": obs_connected,
        "youtube_authed": token is not None,
        "next_schedule": {"id": nxt.id, "start_at": nxt.start_at.isoformat()} if nxt else None,
        "live": live,
    }
