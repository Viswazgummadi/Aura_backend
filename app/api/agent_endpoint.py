from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.agents.graph import graph

router = APIRouter()

class AgentRequest(BaseModel):
    query: str
    user_context: dict = {}

@router.post("/run")
async def run_agent(request: AgentRequest):
    """
    Triggers the Multi-Agent System with a user query.
    """
    try:
        # Initialize State
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "user_context": request.user_context,
            "next": "Supervisor",
            "audit_log": []
        }
        
        # Run Graph
        # We use invoke for synchronous runs (simpler for testing now)
        # In production, this should probably be astream or background task
        final_state = await graph.ainvoke(initial_state)
        
        # Extract response
        messages = [
            {"role": getattr(m, "type", "unknown"), "content": m.content} 
            for m in final_state["messages"]
        ]
        
        return {
            "messages": messages,
            "audit_log": final_state.get("audit_log", [])
        }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
