# nodes/llm.py

from utils.llm_factory import get_llm
from memory.store import get_memory

llm = get_llm()


def llm_node(state):

    memory = get_memory()

    messages = state["messages"]

    # Get AI response
    response = llm.invoke(messages)

    user_msg = messages[-1]
    ai_msg = response.content

    # 🔥 SAVE TO MEM0
    memory.add(
        user_id="manoj",   # later make dynamic
        messages=[
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": ai_msg}
        ]
    )

    return {
        "messages": [response],
        "answer": ai_msg
    }
