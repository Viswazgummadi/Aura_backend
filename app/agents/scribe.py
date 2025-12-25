from langchain_core.messages import AIMessage
from app.agents.common import AgentState

def scribe_node(state: AgentState):
    """
    Worker: Scribe.
    Responsibilities: Email/Message handling.
    """
    # Placeholder Logic
    print("--- SCRIBE: Processing Communication ---")
    return {
        "messages": [AIMessage(content="[Scribe] I have analyzed the communication. It appears to be a meeting request.")],
        "audit_log": [{"role": "Scribe", "action": "Analyzed Email", "status": "Success"}]
    }
