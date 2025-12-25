from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.config import get_settings
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import json
import os

router = APIRouter()
settings = get_settings()

# Scopes required for Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

# For local dev, allow HTTP and relax scope (Google adds openid, etc)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

def create_flow(request: Request = None):
    # Construct config from env vars/settings
    # Note: google-auth-oauthlib expects a client_config dictionary or file
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    redirect_uri = "http://localhost:8000/api/v1/auth/callback/google"
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

@router.get("/login/google")
async def login_google(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google Credentials not configured")
        
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    # In a real app, store state in session to validate callback
    # response = RedirectResponse(authorization_url)
    # response.set_cookie(key="oauth_state", value=state)
    return RedirectResponse(authorization_url)

@router.get("/callback/google")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")
        
    try:
        flow = create_flow()
        flow.fetch_token(code=code)
        
        creds = flow.credentials
        
        # Get User Info
        from googleapiclient.discovery import build
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        email = user_info['email']
        name = user_info.get('name', 'Unknown')
        picture = user_info.get('picture', '')
        
        # Database Logic: Upsert User
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        
        if not user:
            user = User(
                email=email, 
                full_name=name,
                hashed_password="oauth_user" # Placeholder
            )
            db.add(user)
        
        # Update Tokens
        user.google_access_token = creds.token
        user.google_refresh_token = creds.refresh_token
        # user.token_expiry = creds.expiry # If we added this field to model
        
        await db.commit()
        await db.refresh(user)
        
        # Return to Frontend
        # Set a simple cookie for now to indicate "logged in"
        frontend_url = f"http://localhost:3000?auth=success&email={email}&picture={picture}"
        response = RedirectResponse(frontend_url)
        response.set_cookie(key="user_email", value=email, httponly=False)
        if picture:
            response.set_cookie(key="user_picture", value=picture, httponly=False)
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
