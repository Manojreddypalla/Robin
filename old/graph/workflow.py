# graph/workflow.py

from langgraph.graph import StateGraph, START, END

from graph.state import AgentState
from nodes.llm import llm_node


def create_workflow():

    workflow = StateGraph(AgentState)

    workflow.add_node("llm", llm_node)

    workflow.add_edge(START, "llm")
    workflow.add_edge("llm", END)

    return workflow
