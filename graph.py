from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from config import RobinState, MONGO_URI
from nodes import (
    repo_search,
    book_search,
    personal_search,
    oracle,
    router,
    query_rewriter,
    specialist_node,
    chat_node,
)

client       = MongoClient(MONGO_URI)
checkpointer = MongoDBSaver(client)

builder = StateGraph(RobinState)

builder.add_node("router",          router)
builder.add_node("query_rewriter",  query_rewriter)
builder.add_node("repo_search",     repo_search)
builder.add_node("book_search",     book_search)
builder.add_node("personal_search", personal_search)
builder.add_node("specialist",      specialist_node)
builder.add_node("chat",            chat_node)
builder.add_node("oracle",          oracle)

builder.add_edge(START, "router")

builder.add_conditional_edges(
    "router",
    lambda state: state["choice"],
    {
        "repo_search":     "query_rewriter",
        "book_search":     "query_rewriter",
        "personal_search": "personal_search",
        "specialist":      "specialist",
        "chat":            "chat",
        "oracle":          "oracle",
    }
)

builder.add_conditional_edges(
    "query_rewriter",
    lambda state: state.get("choice", "repo_search"),
    {
        "repo_search": "repo_search",
        "book_search": "book_search",
    }
)

builder.add_edge("repo_search",     "oracle")
builder.add_edge("book_search",     "oracle")
builder.add_edge("personal_search", "oracle")
builder.add_edge("specialist",      "oracle")  # FIX #1/#7: oracle summarizes tool output
builder.add_edge("chat",            END)
builder.add_edge("oracle",          END)

robin_app = builder.compile(checkpointer=checkpointer)