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
    """OBS 씬 목록과 DB를 동기화합니다.

    DB 행은 절대 삭제하지 않습니다 (과거 스케줄의 sequence_item.scene_id가
    참조 중일 수 있어, 삭제 시 dangling FK가 발생합니다). 대신 OBS에 존재하는지
    여부만 active 플래그로 갱신합니다.
    """
    obs_scenes = set(obs.list_scenes())
    db_scenes = db.query(Scene).all()

    # 1. 모든 기존 씬의 active 상태를 OBS 실제 목록 기준으로 갱신 (삭제 없음)
    for s in db_scenes:
        s.active = s.obs_scene_name in obs_scenes

    # 2. DB에 없는 새 OBS 씬 추가
    existing_db_names = {s.obs_scene_name for s in db_scenes}
    for name in obs_scenes:
        if name not in existing_db_names:
            db.add(Scene(name=name, obs_scene_name=name, active=True))

    db.commit()
    return {"ok": True}
