from typing import TypedDict, Annotated, Sequence, List, Dict, Any
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """The shared state passed between agents in the graph."""
    # The conversation history. 'operator.add' appends new messages to the list.
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # The next agent to route to. Decided by the Supervisor.
    next: str
    
    # User Context loaded from Guardian (Bio, Preferences, Health status)
    user_context: Dict[str, Any]
    
    # Context specific to the current workflow (e.g., email content being processed)
    current_task_context: Dict[str, Any]
    
    # The proposed schedule or plan being built
    proposed_plan: Dict[str, Any]
    
    # Structural log for UI timeline
    audit_log: List[Dict[str, Any]]
