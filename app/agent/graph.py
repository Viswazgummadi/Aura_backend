from typing import TypedDict, Annotated, Sequence, Any
import operator
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
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

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intermediate_steps: Annotated[list[tuple[Any, Any]], operator.add]

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
    messages = state["messages"]
    
    # Dynamic Configuration
    settings_manager = get_settings_manager()
    config = settings_manager.get_config()
    env_settings = get_settings()
    
    # Prepend System Instruction if exists
    if config.system_instruction:
        # We need to ensure we don't duplicate it if it's already there (naive check)
        # simplistic approach: just insert it at the start. 
        # Ideally, LangGraph state management handles this, but here we modify the list passed to model
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=config.system_instruction)] + messages
    
    # Determine API Key: Dynamic > Env
    api_key = settings_manager.get_active_key()
    
    if not api_key:
        return {"messages": [AIMessage(content="<System>: API Key missing. Please configure it in Settings.")]}

    # Primary Model Selection
    primary_model_id = config.active_model_id
    logger.info(f"Agent Node processing request. Active Model ID: {primary_model_id}")
    
    # Candidate list: Primary first, then fallbacks
    # We construct this dynamically based on available models if we wanted smart fallback,
    # but for now we stick to the user's selected model as primary, and hardcode fallbacks 
    # OR iterating through other available models in config.
    
    # Let's try the active model first.
    candidate_models = [primary_model_id]
    
    # Add simple fallbacks if primary is 'experimental' or specific
    if "flash" in primary_model_id and "gemini-1.5-flash" != primary_model_id:
        candidate_models.append("gemini-1.5-flash") # Stable fallback
    
    last_exception = None

    errors = []
    
    for model_name in candidate_models:
        try:
            # logger.info(f"Attempting model: {model_name}")
            model = ChatGoogleGenerativeAI(
                model=model_name, 
                google_api_key=api_key,
                temperature=0.7
            )
            response = await model.ainvoke(messages)
            return {"messages": [response]}
            
        except Exception as e:
            err_str = str(e)
            logger.error(f"Model {model_name} failed: {err_str}")
            
            # Smart Error Handling
            if "429" in err_str:
                return {
                    "messages": [AIMessage(content=f"⚠️ **System Overload (Rate Limit)**\n\nThe model `{model_name}` is currently rejecting requests due to high traffic or quota limits (Error 429).\n\n*Suggestion*: Try again in a few seconds, or switch to a different model in Settings.")]
                }
            
            errors.append(f"**{model_name}**: {err_str}")
            continue

    # If we get here, all models failed
    error_details = "\n\n".join(errors)
    final_msg = (
        f"❌ **System Error: All attempts failed.**\n\n"
        f"Primary Model: `{primary_model_id}`\n\n"
        f"**Debug Log:**\n{error_details}\n\n"
        f"*Check the 'Debug' tab in Settings for more diagnostics.*"
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
