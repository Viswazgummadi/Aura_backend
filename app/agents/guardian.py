from langchain_core.messages import AIMessage
from app.agents.common import AgentState

def guardian_node(state: AgentState):
    """
    Worker: Guardian.
    Responsibilities: Psychology, Health, & Veto.
    """
    # Placeholder Logic
    print("--- GUARDIAN: Checking Wellbeing ---")
    return {
        "messages": [AIMessage(content="[Guardian] User preference: 'No high-energy tasks after 4 PM'. The 2 PM slot is approved.")],
        "audit_log": [{"role": "Guardian", "action": "Health Check", "status": "Approved"}]
    }
