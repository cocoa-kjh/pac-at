import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from app.main import get_db
from app.config import settings
from app.models import OAuthToken

# YouTube API 접근 권한 스코프 (방송 생성 및 관리를 위해 force-ssl 권한 필요)
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
# 구글 인증 완료 후 리다이렉트될 백엔드 콜백 URL
REDIRECT_URI = f"http://localhost:{settings.port}/auth/youtube/callback"

router = APIRouter(tags=["auth"])


def _flow(**kwargs):
    """클라이언트 시크릿 파일을 읽어와 구글 OAuth 인증 흐름(Flow) 객체를 생성합니다."""
    return Flow.from_client_secrets_file(
        settings.client_secret_path, scopes=SCOPES, redirect_uri=REDIRECT_URI, **kwargs)


@router.get("/auth/youtube")
def youtube_auth():
    """사용자를 구글 로그인 및 OAuth 동의 화면으로 리다이렉트시킵니다.

    * 로컬 개발/디버그 환경의 무상태 콜백을 위해 PKCE 검증기 자동 생성을 끌 수 있도록 설정합니다.
    """
    flow = _flow(autogenerate_code_verifier=False)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                    include_granted_scopes="true")
    return RedirectResponse(url)


@router.get("/auth/youtube/callback")
def youtube_callback(request: Request, db=Depends(get_db)):
    """구글 로그인 후 리다이렉트되어 돌아오는 콜백 엔드포인트입니다.

    인증 코드를 확인하여 액세스 토큰 및 리프레시 토큰을 획득하고, 이를 데이터베이스에 안전하게 저장합니다.
    """
    flow = _flow(autogenerate_code_verifier=False)
    flow.fetch_token(authorization_response=str(request.url))

    creds = flow.credentials
    # 기존 토큰 레코드가 있으면 업데이트하고, 없으면 신규 작성
    token = db.query(OAuthToken).first() or OAuthToken()
    token.access_token = creds.token
    token.refresh_token = creds.refresh_token
    token.expiry = creds.expiry
    token.scopes = " ".join(creds.scopes or SCOPES)
    db.add(token); db.commit()
    
    # 토큰이 갱신되었으므로 백엔드 애플리케이션의 전역 유튜브 클라이언트 리소스를 재빌드합니다.
    from app.main import _build_youtube_client
    request.app.state.youtube = _build_youtube_client()
    
    # 인증이 완료되면 프론트엔드 대시보드 화면(포트 5173)으로 리다이렉트시킵니다.
    return RedirectResponse("http://localhost:5173/")


def load_credentials(db) -> Credentials | None:
    """데이터베이스에서 저장된 OAuth 토큰 정보를 읽어와 google-auth 크레덴셜 객체로 복원합니다."""
    token = db.query(OAuthToken).first()
    if not token or not token.refresh_token:
        return None
    with open(settings.client_secret_path) as f:
        cfg = json.load(f)["web"]
    return Credentials(
        token=token.access_token, refresh_token=token.refresh_token,
        token_uri=cfg["token_uri"], client_id=cfg["client_id"],
        client_secret=cfg["client_secret"], scopes=(token.scopes or "").split())

