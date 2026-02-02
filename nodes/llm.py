# nodes/llm.py

from utils.llm_factory import get_llm


llm = get_llm()


def llm_node(state):

    context = "\n".join(state["memories"])

    system_prompt = f"""
    User Memory:
    {context}
    """

    messages = [
        {"role": "system", "content": system_prompt}
    ] + state["messages"]

    response = llm.invoke(messages)

    return {
        "messages": [response],
        "answer": response.content
    }
