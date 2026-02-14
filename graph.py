from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from config import RobinState, MONGO_URI
from nodes import repo_search, personal_search, oracle, router

# Setup Persistent Memory
client = MongoClient(MONGO_URI)
checkpointer = MongoDBSaver(client)

builder = StateGraph(RobinState)

# Nodes
builder.add_node("repo_search", repo_search)
builder.add_node("personal_search", personal_search)
builder.add_node("oracle", oracle)

# Simplified Routing from START
builder.add_conditional_edges(
    START, 
    router, 
    {
        "repo_search": "repo_search", 
        "personal_search": "personal_search"
    }
)

# Both search nodes lead to the Oracle for the final answer
builder.add_edge("repo_search", "oracle")
builder.add_edge("personal_search", "oracle")

# The Oracle ends the turn
builder.add_edge("oracle", END)

# Compile
robin_app = builder.compile(checkpointer=checkpointer)