from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from database import repo_vault
from mem0 import Memory
# FIXED: Added REPO_COLLECTION and MEM_COLLECTION to the imports
from config import (
    MEMORY_CONFIG, 
    USER_ID, 
    GEMINI_API_KEY, 
    REPO_COLLECTION, 
    MEM_COLLECTION
)

class RobinState(TypedDict):
    messages: Annotated[List, add_messages]
    context: str
    model_choice: str  # "1" for Llama3, "2" for Gemini

# Initialize Models
ollama_llm = ChatOllama(model="llama3", temperature=0.7)
gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY)
memory = Memory.from_config(MEMORY_CONFIG)

def repo_search(state: RobinState):
    query = state["messages"][-1].content
    # Now REPO_COLLECTION is correctly imported and accessible
    print(f"🔍 [THINKING] Searching Technical Vault: {REPO_COLLECTION}...") 
    
    docs = repo_vault.similarity_search(query, k=3)
    
    if docs:
        print(f"✅ [DONE] Found {len(docs)} relevant code snippets.")
        context = "CODE CONTEXT:\n" + "\n".join([d.page_content for d in docs])
    else:
        print("❌ [DONE] No relevant code found.")
        context = "No code context found."
        
    return {"context": context}

def personal_search(state: RobinState):
    query = state["messages"][-1].content
    # Now MEM_COLLECTION is correctly imported and accessible
    print(f"🧠 [THINKING] Accessing Personal Memory: {MEM_COLLECTION}...")
    
    mems = memory.search(query, user_id=USER_ID)
    
    # Handle Mem0 search results robustly
    if isinstance(mems, dict):
        results = mems.get('results', [])
    else:
        results = mems
    
    if results:
        print(f"✅ [DONE] Retrieved {len(results)} personal facts.")
        context = "PERSONAL CONTEXT:\n" + "\n".join([m['memory'] for m in results if 'memory' in m])
    else:
        print("❌ [DONE] No personal memories found.")
        context = "No personal context found."
        
    return {"context": context}

def oracle(state: RobinState):
    # Context-aware system prompt to make Robin feel more "human"
    system_prompt = (
        f"You are Robin, Manoj's personal AI assistant. "
        f"Use the following retrieved context to provide a natural, helpful response.\n\n"
        f"CONTEXT:\n{state.get('context', '')}"
    )
    
    # Select LLM based on user's Streamlit choice
    llm = ollama_llm if state.get("model_choice") == "1" else gemini_llm
    
    response = llm.invoke([("system", system_prompt)] + state["messages"])
    
    # Update memory after generating response
    try:
        memory.add(state["messages"][-1].content, user_id=USER_ID)
    except Exception as e:
        print(f"⚠️ Memory update failed: {e}")
        
    return {"messages": [response]}

def router(state: RobinState):
    text = state["messages"][-1].content.lower()
    # Logic to decide if we need Technical Repo context or Personal Memory
    if any(word in text for word in ["code", "repo", "file", "project", "function", "bug", "script"]):
        return "repo_search"
    return "personal_search"

# Define Graph structure
builder = StateGraph(RobinState)

builder.add_node("repo_search", repo_search)
builder.add_node("personal_search", personal_search)
builder.add_node("oracle", oracle)

builder.add_conditional_edges(
    START, 
    router, 
    {"repo_search": "repo_search", "personal_search": "personal_search"}
)

builder.add_edge("repo_search", "oracle")
builder.add_edge("personal_search", "oracle")
builder.add_edge("oracle", END)

# Final Compiled App
robin_app = builder.compile()