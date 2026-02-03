from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
# Import the logic from your nodes file
from nodes import repo_search, personal_search, oracle, router

class RobinState(TypedDict):
    messages: Annotated[List, add_messages]
    context: str
    model_choice: str 

# Build the Graph
builder = StateGraph(RobinState)

# 1. Add the workers as nodes
builder.add_node("repo_search", repo_search)
builder.add_node("personal_search", personal_search)
builder.add_node("oracle", oracle)

# 2. Define the flow logic
builder.add_conditional_edges(
    START, 
    router, 
    {"repo_search": "repo_search", "personal_search": "personal_search"}
)

builder.add_edge("repo_search", "oracle")
builder.add_edge("personal_search", "oracle")
builder.add_edge("oracle", END)

# 3. Compile the application
robin_app = builder.compile()