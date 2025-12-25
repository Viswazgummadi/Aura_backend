from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from app.agents.common import AgentState
from app.services.google_svc import get_google_service
from app.database import AsyncSessionLocal
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import json

async def timekeeper_node(state: AgentState):
    """
    Worker: Timekeeper.
    Responsibilities: Calendar & Scheduling.
    """
    user_context = state.get("user_context", {})
    user_email = user_context.get("email")
    
    if not user_email:
        return {
            "messages": [AIMessage(content="I cannot access your calendar because I don't know who you are. Please ensure you are logged in and connected to Google.")],
            "audit_log": [{"role": "Timekeeper", "status": "Failed", "reason": "No Email"}]
        }

    # Internal Tool Definition
    async def create_event(summary: str, start_time: str, end_time: str, description: str = ""):
        """Creates a Google Calendar event. Times must be ISO 8601 strings."""
        async with AsyncSessionLocal() as db:
            try:
                service = await get_google_service(user_email, db, "calendar", "v3")
                event_body = {
                    'summary': summary,
                    'description': description,
                    'start': {'dateTime': start_time, 'timeZone': 'UTC'}, 
                    'end': {'dateTime': end_time, 'timeZone': 'UTC'},
                }
                # Check current time context to infer dates if needed? 
                # The LLM should handle ISO conversion ideally.
                
                res = service.events().insert(calendarId='primary', body=event_body).execute()
                link = res.get('htmlLink')
                return f"Event created successfully! Link: {link}"
            except Exception as e:
                return f"Failed to create event: {str(e)}"

    # LLM Setup
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    
    # We define tools interface for binding
    tools = [create_event]
    llm_with_tools = llm.bind_tools(tools)
    
    # Contextualize
    current_time = datetime.now().isoformat()
    system_prompt = f"""You are Timekeeper, an expert scheduler.
    Current Time: {current_time}.
    Your task is to EXECUTE calendar actions requested by the user or supervisor.
    If asked to add an event, USE the `create_event` tool.
    Input times should be converted to absolute ISO 8601 format (YYYY-MM-DDTHH:MM:SS) based on the current time.
    For "today 3pm", calculate the date relative to {current_time}.
    """
    
    # Get last message instructions
    # If the conversation is long, maybe strictly look at the last user message?
    # But Supervisor might have paraphrased it.
    last_message = state["messages"][-1]
    msgs = [SystemMessage(content=system_prompt), last_message]
    
    # Invoke
    response = await llm_with_tools.ainvoke(msgs)
    
    audit_events = []
    final_response_text = response.content

    # Execute Tool Calls
    if response.tool_calls:
        for call in response.tool_calls:
            if call['name'] == 'create_event':
                args = call['args']
                audit_events.append({"role": "Timekeeper", "action": "Calling Tool", "tool": "create_event", "args": args})
                
                # Execute
                tool_result = await create_event(**args)
                
                final_response_text = f"Action Taken: {tool_result}"
                audit_events.append({"role": "Timekeeper", "action": "Tool Result", "result": tool_result})
    
    return {
        "messages": [AIMessage(content=final_response_text)],
        "audit_log": audit_events
    }
