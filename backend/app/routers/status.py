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
        obs.is_streaming()
        obs_connected = True
    except Exception:
        obs_connected = False
    return {
        "obs_connected": obs_connected,
        "youtube_authed": token is not None,
        "next_schedule": {"id": nxt.id, "start_at": nxt.start_at.isoformat()} if nxt else None,
        # live: 실제 스트리밍 상태 연동은 후속(수동 E2E)에서 보강. 현재는 스텁.
        "live": False,
    }
