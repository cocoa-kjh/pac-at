from fastapi import APIRouter, Depends, HTTPException
from app.main import get_db, get_youtube_dep
from app import schemas
from app.models import Broadcast
from app.scheduler.preflight import preflight_broadcast

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


@router.post("", response_model=schemas.BroadcastOut)
def create_broadcast(payload: schemas.BroadcastCreate, db=Depends(get_db)):
    b = Broadcast(**payload.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.get("", response_model=list[schemas.BroadcastOut])
def list_broadcasts(db=Depends(get_db)):
    """로컬 데이터베이스에 저장된 모든 방송 목록을 조회합니다."""
    return db.query(Broadcast).all()


@router.get("/{broadcast_id}/preflight")
def broadcast_preflight(broadcast_id: int, db=Depends(get_db),
                        yt=Depends(get_youtube_dep)):
    b = db.get(Broadcast, broadcast_id)
    if not b:
        raise HTTPException(404)
    return preflight_broadcast(yt, b)


@router.post("/{broadcast_id}/youtube", response_model=schemas.BroadcastOut)
def create_youtube_event(broadcast_id: int, db=Depends(get_db),
                         yt=Depends(get_youtube_dep)):
    """지정한 로컬 방송(broadcast_id)을 유튜브 서버로 전달하여 공식 라이브 스트리밍 이벤트 및 스트림 경로를 생성합니다.

    실행 순서:
    1. 유튜브 라이브 방송 생성 (Live Broadcast)
    2. 유튜브 스트림 키 생성 (Live Stream)
    3. 방송과 스트림 바인딩 (Bind)
    4. 로컬 DB에 생성된 유튜브 아이디와 스트림 키 값을 업데이트하고 상태를 'scheduled'로 변경
    """
    if yt is None: raise HTTPException(status_code=409, detail="YouTube not authenticated")
    b = db.get(Broadcast, broadcast_id)
    if not b: raise HTTPException(404)
    from datetime import datetime, timezone
    
    # 1. 유튜브 라이브 방송 예약 생성
    bid = yt.create_broadcast(b.title, b.description, b.privacy,
                              datetime.now(timezone.utc))
    # 2. 송출 경로(스트림 키) 생성
    stream_id, key, _url = yt.create_stream(f"{b.title} stream")
    # 3. 방송과 스트림 키 연결(바인딩)
    yt.bind(bid, stream_id)
    
    # 4. 로컬 DB 레코드 업데이트
    b.youtube_broadcast_id = bid
    b.youtube_stream_key = key
    b.status = "scheduled"
    db.commit(); db.refresh(b)
    return b

