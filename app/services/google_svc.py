from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

async def get_google_service(user_email: str, db: AsyncSession, service_name: str, version: str):
    """
    Constructs a Google API Service Resource for the given user.
    Handles token refresh if necessary and updates the DB.
    """
    # 1. Fetch User credentials
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()
    
    if not user or not user.google_access_token:
        raise ValueError("User not authenticated with Google")

    # 2. Reconstruct Credentials object
    # The DB stores access_token, refresh_token, etc.
    # Note: We need the scopes if we want to be precise, but usually existing scopes are assumed.
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        # scopes=... (optional if we trust the tokens)
    )

    # 3. Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Update DB with new token
            user.google_access_token = creds.token
            # refresh_token usually stays the same unless revoked/rotated
            await db.commit()
            print(f"Refreshed token for {user_email}")
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            raise ValueError("Token expired and refresh failed")

    # 4. Build Service
    service = build(service_name, version, credentials=creds)
    return service
