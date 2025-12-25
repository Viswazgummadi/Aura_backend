from typing import Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.common import AgentState
from pydantic import BaseModel
import os

# Define the routing options
options = ["Scribe", "Timekeeper", "Strategist", "Guardian"]
# 'FINISH' is a special token to end the graph run
members = options + ["FINISH"]

system_prompt = (
    "You are the Supervisor (Chief of Staff) managing a team of specialized agents: "
    "{members}. "
    "Your role is to route the conversation to the most appropriate worker based on the user's request "
    "and the current state. \n"
    "- 'Scribe': Handles reading, writing, and analyzing emails/messages.\n"
    "- 'Timekeeper': Handles calendar checks, scheduling, and time availability.\n"
    "- 'Strategist': Handles complex task breakdown, planning, and estimation.\n"
    "- 'Guardian': Handles user psychology, health checks, stress management, and veto powers.\n\n"
    "Do not perform the tasks yourself. Only route. "
    "If the user's request is fully addressed or requires human input, route to 'FINISH'."
)

class RouteResponse(BaseModel):
    next: Literal["Scribe", "Timekeeper", "Strategist", "Guardian", "FINISH"]

def supervisor_node(state: AgentState):
    """
    The orchestrator node. Decides which agent acts next.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Given the conversation above, who should act next? Select one: {members}"),
    ]).partial(members=", ".join(members))

    # We use with_structured_output to force a valid routing decision
    chain = prompt | llm.with_structured_output(RouteResponse)
    
    response = chain.invoke(state)
    return {"next": response.next}
