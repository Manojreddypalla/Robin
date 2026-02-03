import time
from langchain_ollama import ChatOllama
from database import repo_vault
from memory_engine import search_memory, add_to_memory

llm = ChatOllama(model="llama3", temperature=0.7)

def repo_search(state):
    query = state["messages"][-1].content
    print(f"\n[THINKING] 🔍 Searching: 'robin_knowledge'...")
    docs = repo_vault.similarity_search(query, k=3)
    context = "CODE:\n" + "\n".join([d.page_content for d in docs]) if docs else "No code found."
    print(f"[DONE] ✅ Context retrieved.")
    return {"context": context}

def personal_search(state):
    query = state["messages"][-1].content
    print(f"\n[THINKING] 🧠 Searching: 'robin_memories'...")
    mems = search_memory(query)
    context = "PERSONAL:\n" + "\n".join([m['memory'] for m in mems['results']])
    print(f"[DONE] ✅ Memory retrieved.")
    return {"context": context}

def oracle(state):
    system_prompt = f"You are Robin. Assist Manoj (Graduating July 2026).\n{state.get('context','')}"
    response = llm.invoke([("system", system_prompt)] + state["messages"])
    add_to_memory(state["messages"][-1].content)
    return {"messages": [response]}