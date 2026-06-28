from fastapi import APIRouter, Depends, HTTPException
from app.main import get_db, get_youtube_dep
from app import schemas
from app.models import Broadcast

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])

@router.post("", response_model=schemas.BroadcastOut)
def create_broadcast(payload: schemas.BroadcastCreate, db=Depends(get_db)):
    b = Broadcast(**payload.model_dump()); db.add(b); db.commit(); db.refresh(b)
    return b

@router.get("", response_model=list[schemas.BroadcastOut])
def list_broadcasts(db=Depends(get_db)):
    return db.query(Broadcast).all()

@router.post("/{broadcast_id}/youtube", response_model=schemas.BroadcastOut)
def create_youtube_event(broadcast_id: int, db=Depends(get_db),
                         yt=Depends(get_youtube_dep)):
    b = db.get(Broadcast, broadcast_id)
    if not b: raise HTTPException(404)
    from datetime import datetime, timezone
    bid = yt.create_broadcast(b.title, b.description, b.privacy,
                              datetime.now(timezone.utc))
    stream_id, key, _url = yt.create_stream(f"{b.title} stream")
    yt.bind(bid, stream_id)
    b.youtube_broadcast_id = bid
    b.youtube_stream_key = key
    b.status = "scheduled"
    db.commit(); db.refresh(b)
    return b
