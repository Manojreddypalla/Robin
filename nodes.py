import time
import re
import uuid
import logging
from typing import List

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage

from database import repo_vault
from memory_engine import search_memory, add_to_memory
from prompts import get_combined_prompt
from config import GEMINI_KEYS, RobinState

# --- LOGGING CONFIG ---
logging.getLogger("httpx").setLevel(logging.WARNING)

# ============================
# 🔑 KEY ROTATION & LLM CONFIG
# ============================
current_key_index = 0

def get_current_gemini():
    """Cycles through the 6 Gemini keys with a fallback safety."""
    global current_key_index
    idx = current_key_index % len(GEMINI_KEYS)
    api_key = GEMINI_KEYS[idx]
    
    print(f"🔑 [SYSTEM] Active Key #{idx + 1}")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.2, # Lower for technical accuracy
        request_timeout=15
    )

# Initialize Local Llama 3 for the Circuit Breaker
ollama_llm = ChatOllama(model="llama3", temperature=0.7)

# ============================
# 🚦 THE ARCHITECT ROUTER
# ============================

def router(state: RobinState):
    """
    Intelligently routes the flow:
    - Code/Files -> repo_search
    - Personal History -> personal_search
    - General -> oracle
    """
    user_input = state["messages"][-1].content.lower()
    
    # 1. Technical/Code Triggers (The Vault)
    repo_triggers = [".py", "code", "repo", "function", "class", "file", "database", "logic", "ingest"]
    if any(k in user_input for k in repo_triggers):
        print("📍 Path: repo_search | Logic: Codebase retrieval")
        return "repo_search"

    # 2. Default to Personal Memory
    return "personal_search"

# ============================
# 🛠️ RAG NODES
# ============================

def repo_search(state: RobinState):
    """Queries Qdrant for technical snippets."""
    query = state["messages"][-1].content
    print(f"🔍 [ROBIN] Extracting from Vault...")
    try:
        docs = repo_vault.similarity_search(query, k=4) # Increased k for better context
        context = "TECHNICAL DOCS:\n" + "\n".join([d.page_content for d in docs])
    except:
        context = "Vault search failed."
    return {"context": context}

def personal_search(state: RobinState):
    """Queries Mem0/Memory for personal context."""
    query = state["messages"][-1].content
    print(f"🧠 [ROBIN] Recalling Memory...")
    try:
        mems = search_memory(query)
        context = "PERSONAL HISTORY:\n" + "\n".join(mems)
    except:
        context = "Memory recall failed."
    return {"context": context}

# ============================
# 🔮 THE ORACLE (The Brain)
# ============================

def oracle(state: RobinState):
    """Reasoning engine with automatic Cloud-to-Local fallback."""
    global current_key_index
    context = state.get("context", "")
    
    # Build the prompt using your combined template
    prompt = f"""
    {get_combined_prompt(context)}
    STRICT RULES:
    1. If the context contains code, analyze it line-by-line.
    2. Tone: Senior Technical Architect. No fluff.
    """
    
    messages = [SystemMessage(content=prompt)] + state["messages"]
    response = None

    # --- PHASE 1: CLOUD REASONING (Gemini) ---
    if str(state.get("model_choice")) == "2":
        attempts = 0
        while attempts < len(GEMINI_KEYS):
            try:
                llm = get_current_gemini()
                response = llm.invoke(messages)
                break 
            except Exception as e:
                # If 429 Quota Error, wait 2 seconds before rotating
                if "429" in str(e):
                    print(f"⚠️ Key #{current_key_index + 1} Exhausted. Waiting 2s...")
                    time.sleep(2)
                
                current_key_index = (current_key_index + 1) % len(GEMINI_KEYS)
                attempts += 1

    # --- PHASE 2: LOCAL CIRCUIT BREAKER (Llama 3) ---
    if not response:
        print("🌪️ [ROBIN] Falling back to Local Llama 3 (RTX 4060 Enabled)...")
        try:
            response = ollama_llm.invoke(messages)
        except Exception as e:
            return {"messages": [AIMessage(content=f"FATAL ERROR: Both Cloud and Local failed. {e}")]}

    # --- PHASE 3: ATOMIC MEMORY SAVE ---
    if response and response.content:
        try:
            # Sync the new information to Mem0
            add_to_memory(state["messages"][-1].content, response.content)
            print("✅ Memory Updated.")
        except:
            pass
    
    return {"messages": [response]}