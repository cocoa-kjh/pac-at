from fastapi import APIRouter, Depends
from app.main import get_db, get_obs_dep
from app.models import OAuthToken, Schedule

router = APIRouter(tags=["status"])

@router.get("/status")
def status(db=Depends(get_db), obs=Depends(get_obs_dep)):
    token = db.query(OAuthToken).first()
    nxt = (db.query(Schedule)
             .filter(Schedule.status == "pending")
             .order_by(Schedule.start_at).first())
    try:
        obs_connected = obs.is_streaming() is not None
    except Exception:
        obs_connected = False
    return {
        "obs_connected": obs_connected,
        "youtube_authed": token is not None,
        "next_schedule": {"id": nxt.id, "start_at": nxt.start_at.isoformat()} if nxt else None,
        "live": bool(token) and False,
    }
