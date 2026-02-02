# nodes/retrieve.py

from memory.client import get_memory_client


# Create memory client once
memory = get_memory_client()


def memory_retrieve(state):
    """
    Fetch relevant memories from Qdrant + Neo4j
    """

    # Get latest user message
    user_query = state["messages"][-1]

    # Search in mem0
    results = memory.search(
        query=user_query,
        user_id="manoj"
    )

    # Extract memory text
    memories = [
        item["memory"]
        for item in results.get("results", [])
    ]

    return {
        "memories": memories
    }
