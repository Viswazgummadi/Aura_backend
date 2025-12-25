from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User
from app.agent.graph import create_agent_graph
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    model_id: Optional[str] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Initialize graph
    app = create_agent_graph()
    
    # Extract values
    message = request.message
    thread_id = request.thread_id
    
    # Handle Thread Creation or Retrieval
    if not thread_id:
        # Create new thread if none provided (optional behavior, could also require explicit creation)
        import uuid
        from app.models import Thread
        thread_id = str(uuid.uuid4())
        # Auto-title based on first message
        title = message[:50] + "..." if len(message) > 50 else message
        new_thread = Thread(id=thread_id, title=title)
        db.add(new_thread)
        await db.commit()
    
    # Persist User Message
    from app.models import Message
    user_msg = Message(thread_id=thread_id, role="user", content=message)
    db.add(user_msg)
    await db.commit()

    # Retrieve history? 
    # Ideally, we should fetch previous messages from DB and pass to agent.
    # For now, we will just pass the current message, assuming the agent/graph works statelessly per request 
    # unless we rebuild history here.
    # Let's rebuild history for context!
    from sqlalchemy import select
    result = await db.execute(select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at.asc()))
    history = result.scalars().all()
    
    # Convert to LangChain messages
    from langchain_core.messages import HumanMessage, AIMessage
    langchain_messages = []
    for msg in history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
    
    # Run graph with full history
    # Note: 'messages' key in state will usually be appended to. 
    # If using a pre-built graph that expects full state, we pass it all.
    inputs = {"messages": langchain_messages} # This replaces state? depends on graph definition.
    # If graph uses 'messages' as Annotated[list, add_messages], passing full list might duplicate if we are not careful.
    # Since we are essentially "rehydrating" the state, passing full history is correct for a stateless REST API model.
    
    result = await app.ainvoke(inputs)
    
    # Parse result
    # LangGraph returns all messages. We want the last one which is the new AI response.
    last_message = result["messages"][-1]
    
    # Persist AI Response
    ai_msg = Message(thread_id=thread_id, role="assistant", content=last_message.content)
    db.add(ai_msg)
    await db.commit()
    
    return {"response": last_message.content, "thread_id": thread_id}

@router.get("/auth/login")
async def login_google():
    return {"message": "Redirect to Google Auth URL (Todo)"}

@router.get("/auth/callback")
async def auth_callback(code: str, db: AsyncSession = Depends(get_db)):
    return {"message": "Process callback (Todo)"}
