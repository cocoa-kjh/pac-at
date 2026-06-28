from fastapi import APIRouter, Depends
from app.main import get_db, get_obs_dep
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

@router.post("/sync")
def sync_scenes(db=Depends(get_db), obs=Depends(get_obs_dep)):
    existing = {s.obs_scene_name for s in db.query(Scene).all()}
    for name in obs.list_scenes():
        if name not in existing:
            db.add(Scene(name=name, obs_scene_name=name))
    db.commit()
    return {"ok": True}
