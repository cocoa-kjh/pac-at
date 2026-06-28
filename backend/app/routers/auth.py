import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from app.main import get_db
from app.config import settings
from app.models import OAuthToken

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
REDIRECT_URI = f"http://localhost:{settings.port}/auth/youtube/callback"

router = APIRouter(tags=["auth"])

def _flow():
    return Flow.from_client_secrets_file(
        settings.client_secret_path, scopes=SCOPES, redirect_uri=REDIRECT_URI)

@router.get("/auth/youtube")
def youtube_auth():
    flow = _flow()
    url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                    include_granted_scopes="true")
    return RedirectResponse(url)

@router.get("/auth/youtube/callback")
def youtube_callback(request: Request, db=Depends(get_db)):
    flow = _flow()
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    token = db.query(OAuthToken).first() or OAuthToken()
    token.access_token = creds.token
    token.refresh_token = creds.refresh_token
    token.expiry = creds.expiry
    token.scopes = " ".join(creds.scopes or SCOPES)
    db.add(token); db.commit()
    return RedirectResponse("http://localhost:5173/")

def load_credentials(db) -> Credentials | None:
    token = db.query(OAuthToken).first()
    if not token or not token.refresh_token:
        return None
    with open(settings.client_secret_path) as f:
        cfg = json.load(f)["web"]
    return Credentials(
        token=token.access_token, refresh_token=token.refresh_token,
        token_uri=cfg["token_uri"], client_id=cfg["client_id"],
        client_secret=cfg["client_secret"], scopes=(token.scopes or "").split())
