from fastapi import APIRouter, Depends
from app.main import get_db
from app import schemas
from app.models import Scene

router = APIRouter(prefix="/scenes", tags=["scenes"])

@router.post("", response_model=schemas.SceneOut)
def create_scene(payload: schemas.SceneCreate, db=Depends(get_db)):
    s = Scene(**payload.model_dump()); db.add(s); db.commit(); db.refresh(s)
    return s

@router.get("", response_model=list[schemas.SceneOut])
def list_scenes(db=Depends(get_db)):
    return db.query(Scene).all()
