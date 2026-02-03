import os
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from mem0 import Memory
import time

# --- 1. CONFIGURATION ---
USER_ID = "manoj_palla"
QDRANT_URL = "http://localhost:6333"
REPO_COLLECTION = "robin_knowledge"

# Initialize Models
llm = ChatOllama(model="llama3", temperature=0.7)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Initialize Qdrant Client & Repo Collection
client = QdrantClient(url=QDRANT_URL)
repo_vault = QdrantVectorStore(
    client=client, 
    collection_name=REPO_COLLECTION, 
    embedding=embeddings
)

# Initialize mem0 (Personal Memory)
memory = Memory.from_config({
    "vector_store": {
        "provider": "qdrant", 
        "config": {
            "url": QDRANT_URL, 
            "collection_name": "robin_memories",
            "embedding_model_dims": 768
        }
    },
    "embedder": {
        "provider": "ollama", 
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://127.0.0.1:11434" # Use IP instead of localhost
        }
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3",
            "ollama_base_url": "http://127.0.0.1:11434"
        }
    }
})

# --- 2. STATE DEFINITION ---
class RobinState(TypedDict):
    messages: Annotated[List, add_messages]
    context: str

# --- 3. NODES ---

def router(state: RobinState):
    """Routing logic: If user asks about code/repo, go to repo_search."""
    last_msg = state["messages"][-1].content.lower()
    if any(word in last_msg for word in ["code", "repo", "function", "file", "script", "project data"]):
        return "repo_search"
    return "personal_search"

def repo_search(state: RobinState):
    """Retrieves code snippets from Qdrant with status update."""
    query = state["messages"][-1].content
    
    # --- THINKING STATUS ---
    print(f"\n[THINKING] 🔍 Searching database: '{REPO_COLLECTION}'...")
    time.sleep(0.5) # Small delay to make it feel like "thinking" for the demo
    
    docs = repo_vault.similarity_search(query, k=3)
    
    if not docs:
        context = "No relevant code found."
        print(f"[DONE] ❌ No data found in '{REPO_COLLECTION}'.")
    else:
        context = "\n\nCODE CONTEXT:\n" + "\n".join([d.page_content for d in docs])
        print(f"[DONE] ✅ Found {len(docs)} relevant code snippets.")
    
    return {"context": context}

def personal_search(state: RobinState):
    """Retrieves personal facts from mem0 with status update."""
    query = state["messages"][-1].content
    
    # --- THINKING STATUS ---
    print(f"\n[THINKING] 🧠 Searching database: 'robin_memories' (Personal Context)...")
    time.sleep(0.5)
    
    mems = memory.search(query, user_id=USER_ID)
    
    if not mems['results']:
        context = "No personal memory found."
        print(f"[DONE] ❌ No personal data found.")
    else:
        context = "\n\nPERSONAL CONTEXT:\n" + "\n".join([m['memory'] for m in mems['results']])
        print(f"[DONE] ✅ Retrieved {len(mems['results'])} personal facts.")
        
    return {"context": context}

def oracle(state: RobinState):
    """Robin generates her final response."""
    system_prompt = (
        "You are Robin, a personal AI agent and code archaeologist. "
        "Use the provided context to assist Manoj. "
        "Manoj graduates in July 2026. Be helpful and technical."
        f"\n{state.get('context', '')}"
    )
    
    # 1. Get the response first so the user isn't waiting
    response = llm.invoke([("system", system_prompt)] + state["messages"])
    
    # 2. Try to save to memory, but don't crash if it fails
    try:
        memory.add(state["messages"][-1].content, user_id=USER_ID)
    except Exception as e:
        print(f"\n[SYSTEM] ⚠️ Minor memory sync error: {e}")
    
    return {"messages": [response]}

# --- 4. GRAPH ASSEMBLY ---
builder = StateGraph(RobinState)
builder.add_node("repo_search", repo_search)
builder.add_node("personal_search", personal_search)
builder.add_node("oracle", oracle)

builder.add_conditional_edges(START, router, {"repo_search": "repo_search", "personal_search": "personal_search"})
builder.add_edge("repo_search", "oracle")
builder.add_edge("personal_search", "oracle")
builder.add_edge("oracle", END)

robin = builder.compile()

# --- 5. CHAT LOOP ---
if __name__ == "__main__":
    print("🚢 Robin: 'Connected to Repo and Memory vaults. Ready, Manoj.'")
    thread_messages = []
    while True:
        user_input = input("\n👤 Manoj: ")
        if user_input.lower() in ["exit", "quit"]: break
        
        thread_messages.append(("user", user_input))
        result = robin.invoke({"messages": thread_messages})
        
        reply = result["messages"][-1].content
        thread_messages.append(("assistant", reply))
        print(f"\n🚢 Robin: {reply}")