from fastapi import APIRouter, Depends
from app.main import get_db
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
