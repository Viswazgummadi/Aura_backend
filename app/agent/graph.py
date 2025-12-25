from typing import TypedDict, Annotated, Sequence, Any
import operator
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings

settings = get_settings()


# Define Tools
from app.agent.tools.dummy import dummy_tools # Fallback
from app.agent.tools.gmail import GmailTool
from app.agent.tools.calendar import CalendarTool
from app.agent.tools.tasks import TaskTool
from app.models import User
from app.database import AsyncSessionLocal
from app.services.google_svc import get_google_service

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intermediate_steps: Annotated[list[tuple[Any, Any]], operator.add]
    user_context: dict

def get_model():
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set")
    
    return ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.7
    )

import logging

logger = logging.getLogger(__name__)

from app.core.settings_manager import get_settings_manager
from app.config import get_settings # Keep for env fallback if needed

# ... (Previous imports remain, ensure to keep others if not modifying)

async def agent_node(state: AgentState):
    """
    Process the user input and generate a response using the selected model.
    Includes fallback logic if the primary model fails.
    """
    # Context Extraction
    user_context = state.get("user_context", {})
    user_email = user_context.get("email")
    
    # Internal Tool Definition (Context-Aware)
    async def create_event(summary: str, start_time: str, end_time: str, description: str = ""):
        """Creates a Google Calendar event. Times must be ISO 8601 strings (e.g. 2024-01-01T10:00:00)."""
        if not user_email:
            return "Error: User email not found. Cannot access calendar."
            
        async with AsyncSessionLocal() as db:
            try:
                service = await get_google_service(user_email, db, "calendar", "v3")
                event_body = {
                    'summary': summary,
                    'description': description,
                    'start': {'dateTime': start_time, 'timeZone': 'UTC'}, 
                    'end': {'dateTime': end_time, 'timeZone': 'UTC'},
                }
                res = service.events().insert(calendarId='primary', body=event_body).execute()
                link = res.get('htmlLink')
                return f"Event created successfully! Link: {link}"
            except Exception as e:
                return f"Failed to create event: {str(e)}"

    # Dynamic Configuration
    settings_manager = get_settings_manager()
    config = settings_manager.get_config()
    
    # Time Context
    from datetime import datetime
    current_time = datetime.now().isoformat()
    
    # Base Instruction
    base_instruction = config.system_instruction or "You are Aura, a helpful agent."
    time_instruction = f"\nCurrent Time: {current_time}. If asked to schedule, use `create_event` with ISO 8601 times."
    
    messages = [SystemMessage(content=base_instruction + time_instruction)] + state["messages"]
    
    # Primary Model Selection
    primary_id = settings_manager.get_active_model_resolved_id()
    
    # Candidate Models (Primary -> Fallback)
    candidate_models = [primary_id]
    
    # Smart Fallback Logic
    # User requested: Base=2.5-lite, Fallback=2.5-flash.
    # If primary is 2.5-flash-lite, add 2.5-flash as fallback
    if "lite" in primary_id and "gemini-2.5-flash" != primary_id:
        candidate_models.append("gemini-2.5-flash")
    elif "flash" in primary_id and "gemini-1.5-flash" != primary_id:
        # If user selected 2.5-flash, maybe add 1.5 as last resort? 
        # User explicitly said "1.5 models are out of service", so we SKIP 1.5.
        pass

    # Candidate Keys (Active -> Others)
    candidate_keys = settings_manager.get_all_api_keys()
    if not candidate_keys:
        return {"messages": [AIMessage(content="<System>: No API Keys configured.")]}

    errors = []
    
    for model_name in candidate_models:
        for i, api_key in enumerate(candidate_keys):
            try:
                # logger.info(f"Attempting: Model={model_name}, KeyIndex={i}")
                model = ChatGoogleGenerativeAI(
                    model=model_name, 
                    google_api_key=api_key,
                    temperature=0
                )
                
                # Bind Tools
                tools = [create_event]
                model_with_tools = model.bind_tools(tools)
                
                response = await model_with_tools.ainvoke(messages)
                
                # Tool Execution Loop (Simple Single-Turn)
                if response.tool_calls:
                    tool_results = []
                    for call in response.tool_calls:
                        if call['name'] == 'create_event':
                            logger.info(f"Executing create_event: {call['args']}")
                            res = await create_event(**call['args'])
                            tool_results.append(ToolMessage(tool_call_id=call['id'], content=str(res), name=call['name']))
                    
                    if tool_results:
                        messages.append(response)
                        messages.extend(tool_results)
                        final_response = await model_with_tools.ainvoke(messages)
                        return {"messages": [response, *tool_results, final_response]}
                
                return {"messages": [response]}
                
            except Exception as e:
                err_str = str(e)
                logger.error(f"Failed: Model={model_name} KeyIndex={i} Error={err_str}")
                
                if "429" in err_str:
                    # Rate Limit -> Try next key immediately
                    continue
                
                # Other errors (Auth, etc) -> Try next key too
                errors.append(f"[{model_name}/Key{i}]: {err_str}")
                continue

    # If we get here, all combinations failed
    error_details = "\n".join(errors[:5]) # Truncate
    final_msg = (
        f"❌ **System Exhausted**\n\n"
        f"Tried {len(candidate_models)} models and {len(candidate_keys)} API keys.\n"
        f"All attempts failed. Please check your network or quota.\n\n"
        f"**Last Errors:**\n{error_details}"
    )
    return {"messages": [AIMessage(content=final_msg)]}

# Define the graph
def create_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    # workflow.add_node("tools", ToolNode(dummy_tools))
    
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END) # Simplified for now
    
    return workflow.compile()
