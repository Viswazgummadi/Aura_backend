from langchain_core.messages import AIMessage
from app.agents.common import AgentState

def strategist_node(state: AgentState):
    """
    Worker: Strategist.
    Responsibilities: Task breakdown and planning.
    """
    # Placeholder Logic
    print("--- STRATEGIST: Optimizing Plan ---")
    return {
        "messages": [AIMessage(content="[Strategist] Breaking this down: We need 2 focused hours. I recommend the Pomodoro technique.")],
        "audit_log": [{"role": "Strategist", "action": "Created Plan", "status": "Optimized"}]
    }
