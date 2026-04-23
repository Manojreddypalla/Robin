from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, AIMessage

# --- 🌐 WEB SEARCH TOOL ---
# We initialize the wrapper here
ddg_search = DuckDuckGoSearchRun()

@tool
def search_web_news(query: str):
    """
    Search the live web for the latest AI news, tech updates, or RSS-style feeds.
    Use this for: 'latest news', 'what happened today in AI', or 'current version of...'.
    """
    print(f"🌐 [TOOL] DuckDuckGo searching: {query}")
    try:
        return ddg_search.run(query)
    except Exception as e:
        return f"Web search failed: {e}"

# --- 🛠️ TOOL REGISTRY ---
# Added this to the list of tools Gemini can access
tools = [search_web_news]

# ============================
# 🔮 THE ORACLE (The Brain)
# ============================
def oracle(state: RobinState):
    global current_key_index
    context = state.get("context", "")
    
    # 1. Initialize the Brain
    llm = get_current_gemini()
    
    # 2. 🚀 BIND TOOLS: This allows Gemini to 'choose' the web search
    llm_with_tools = llm.bind_tools(tools)
    
    # 3. Assemble Prompt
    prompt = get_combined_prompt(context)
    messages = [SystemMessage(content=prompt)] + state["messages"]
    
    response = None

    # --- PHASE 1: CLOUD REASONING (Gemini 2.5 Flash) ---
    if str(state.get("model_choice")) == "2":
        attempts = 0
        while attempts < len(GEMINI_KEYS):
            try:
                # LLM decides if it needs the 'search_web_news' tool
                response = llm_with_tools.invoke(messages)
                break 
            except Exception as e:
                current_key_index = (current_key_index + 1) % len(GEMINI_KEYS)
                attempts += 1

    # --- PHASE 2: LOCAL FALLBACK ---
    if not response:
        print("🌪️ [ROBIN] Falling back to Local Llama 3 (No Web Tools)...")
        try:
            # Note: Local Llama 3 usually doesn't support tool calling without extra config,
            # so we just let it talk directly.
            response = ollama_llm.invoke(messages)
        except Exception as e:
            return {"messages": [AIMessage(content=f"FATAL ERROR: {e}")]}

    # --- PHASE 3: ATOMIC MEMORY SAVE ---
    if response and response.content:
        try:
            add_to_memory(state["messages"][-1].content, response.content)
            print("✅ Conversation fact-checked and saved.")
        except Exception as e:
            print(f"⚠️ Memory save bypassed: {e}")
    
    return {"messages": [response]}