from langgraph.graph import StateGraph, END
from app.agents.common import AgentState
from app.agents.supervisor import supervisor_node
from app.agents.scribe import scribe_node
from app.agents.timekeeper import timekeeper_node
from app.agents.strategist import strategist_node
from app.agents.guardian import guardian_node

# 1. Initialize Graph
workflow = StateGraph(AgentState)

# 2. Add Nodes
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Scribe", scribe_node)
workflow.add_node("Timekeeper", timekeeper_node)
workflow.add_node("Strategist", strategist_node)
workflow.add_node("Guardian", guardian_node)

# 3. Define Entry Point
workflow.set_entry_point("Supervisor")

# 4. Define Conditional Edges (Routing)
# The Supervisor output {"next": "AgentName"} determines the path
workflow.add_conditional_edges(
    "Supervisor",
    lambda state: state["next"],
    {
        "Scribe": "Scribe",
        "Timekeeper": "Timekeeper",
        "Strategist": "Strategist",
        "Guardian": "Guardian",
        "FINISH": END
    }
)

# 5. Define Worker -> Supervisor Edges
# Workers always report back to Supervisor to decide next steps
workflow.add_edge("Scribe", "Supervisor")
workflow.add_edge("Timekeeper", "Supervisor")
workflow.add_edge("Strategist", "Supervisor")
workflow.add_edge("Guardian", "Supervisor")

# 6. Compile
graph = workflow.compile()
