from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.google_svc import get_google_service
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

router = APIRouter()

class CalendarEvent(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: str # ISO format
    end_time: str   # ISO format
    location: Optional[str] = None

@router.get("/events")
async def list_events(
    user_email: str, # We'll pass this from frontend for now (in prod -> Auth header)
    time_min: Optional[str] = None, 
    time_max: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Defaults to current month if not provided
        if not time_min:
            time_min = datetime.utcnow().replace(day=1).isoformat() + 'Z'
        if not time_max:
             # Next month roughly
             time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'

        service = await get_google_service(user_email, db, "calendar", "v3")
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=time_min, 
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events

    except Exception as e:
        print(f"Calendar Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/events")
async def create_event(
    user_email: str,
    event: CalendarEvent,
    db: AsyncSession = Depends(get_db)
):
    try:
        service = await get_google_service(user_email, db, "calendar", "v3")
        
        event_body = {
            'summary': event.summary,
            'location': event.location,
            'description': event.description,
            'start': {'dateTime': event.start_time, 'timeZone': 'UTC'}, # Simplify TZ for now
            'end': {'dateTime': event.end_time, 'timeZone': 'UTC'},
        }
        
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return created_event

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    user_email: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        service = await get_google_service(user_email, db, "calendar", "v3")
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"status": "deleted", "id": event_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/events/{event_id}")
async def update_event(
    event_id: str,
    user_email: str,
    event: CalendarEvent,
    db: AsyncSession = Depends(get_db)
):
    try:
        service = await get_google_service(user_email, db, "calendar", "v3")
        
        # First get existing to preserve fields if needed, but for patch we might just update what we have
        # Google API 'patch' method supports partial updates
        
        event_body = {
            'summary': event.summary,
            'description': event.description,
            'location': event.location,
            'start': {'dateTime': event.start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': event.end_time, 'timeZone': 'UTC'},
        }
        
        # Filter None
        event_body = {k: v for k, v in event_body.items() if v is not None}

        updated_event = service.events().patch(calendarId='primary', eventId=event_id, body=event_body).execute()
        return updated_event
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
