# graph/state.py

from typing_extensions import TypedDict
from typing import Annotated, List
from langgraph.graph.message import add_messages


class AgentState(TypedDict):

    # Chat history
    messages: Annotated[list, add_messages]

    # Retrieved memories (future use)
    memories: List[str]

    # Final answer
    answer: str
