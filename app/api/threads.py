from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Thread, Message

router = APIRouter()

# Schema
class MessageSchema(BaseModel):
    id: int
    thread_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ThreadCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ThreadListSchema(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    # No messages here to avoid lazy load issues

    class Config:
        from_attributes = True

class ThreadDetailSchema(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    messages: List[MessageSchema] = []

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ThreadListSchema])
async def list_threads(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Thread).order_by(Thread.updated_at.desc()).offset(skip).limit(limit))
    threads = result.scalars().all()
    return threads

@router.post("/", response_model=ThreadDetailSchema)
async def create_thread(thread_in: ThreadCreate, db: AsyncSession = Depends(get_db)):
    new_thread = Thread(
        id=str(uuid.uuid4()),
        title=thread_in.title
    )
    db.add(new_thread)
    await db.commit()
    # Eager load messages (empty) to satisfy schema
    # await db.refresh(new_thread, attribute_names=["messages"]) 
    # Actually just refreshing object should work if we access it, but let's be safe
    # Re-query with eager load
    result = await db.execute(select(Thread).options(selectinload(Thread.messages)).where(Thread.id == new_thread.id))
    new_thread_loaded = result.scalar_one()
    return new_thread_loaded

@router.get("/{thread_id}", response_model=ThreadDetailSchema)
async def get_thread(thread_id: str, db: AsyncSession = Depends(get_db)):
    # Use selectinload to eagerly load messages
    result = await db.execute(
        select(Thread)
        .options(selectinload(Thread.messages))
        .where(Thread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return thread


@router.delete("/{thread_id}")
async def delete_thread(thread_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    await db.delete(thread)
    await db.commit()
    return {"status": "success"}
