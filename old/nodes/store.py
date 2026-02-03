# nodes/store.py

from memory.client import get_memory_client


# Create memory client once
memory = get_memory_client()


def memory_store(state):
    """
    Save conversation into Qdrant + Neo4j
    """

    # Get last user + AI message
    user_msg = state["messages"][-2]
    ai_msg = state["messages"][-1]

    # Save to mem0
    memory.add(
        user_id="manoj",
        messages=[
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": ai_msg}
        ]
    )

    return state
