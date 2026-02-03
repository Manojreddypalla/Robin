from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from nodes import repo_search, personal_search, oracle

class RobinState(TypedDict):
    messages: Annotated[List, add_messages]
    context: str

def router(state):
    text = state["messages"][-1].content.lower()
    if any(word in text for word in ["code", "repo", "function", "project"]):
        return "repo_search"
    return "personal_search"

builder = StateGraph(RobinState)
builder.add_node("repo_search", repo_search)
builder.add_node("personal_search", personal_search)
builder.add_node("oracle", oracle)

builder.add_conditional_edges(START, router, {"repo_search": "repo_search", "personal_search": "personal_search"})
builder.add_edge("repo_search", "oracle")
builder.add_edge("personal_search", "oracle")
builder.add_edge("oracle", END)

robin_app = builder.compile()