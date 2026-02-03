import time
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from database import repo_vault
from memory_engine import search_memory, add_to_memory, mem_client
from prompts import get_combined_prompt
from config import USER_ID, GEMINI_API_KEY, REPO_COLLECTION, MEM_COLLECTION
from config import RobinState

# Initialize Models
ollama_llm = ChatOllama(model="llama3", temperature=0.7)
gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

def repo_search(state):
    query = state["messages"][-1].content
    print(f"\n🔍 [THINKING] Searching Technical Vault: {REPO_COLLECTION}...")
    
    docs = repo_vault.similarity_search(query, k=3)
    context = "CODE CONTEXT:\n" + "\n".join([d.page_content for d in docs]) if docs else "No technical code found."
    
    print(f"✅ [DONE] Repository context retrieved.")
    return {"context": context}

def personal_search(state):
    query = state["messages"][-1].content
    print(f"\n🧠 [THINKING] Accessing Personal Memory: {MEM_COLLECTION}...")
    
    mems = search_memory(query)
    context = "PERSONAL CONTEXT:\n" + "\n".join(mems) if mems else "No personal memories found."
    
    print(f"✅ [DONE] Personal context retrieved.")
    return {"context": context}

def oracle(state: RobinState):
    context = state.get('context', '')
    system_prompt = get_combined_prompt(context)
    
    # Selection logic for Gemini vs Llama
    llm = ollama_llm if state.get("model_choice") == "1" else gemini_llm
    
    response = llm.invoke([("system", system_prompt)] + state["messages"])
    
    # VALIDATION: Prevent sending empty content to the embedder
    user_content = state["messages"][-1].content
    assistant_content = response.content

    if user_content and assistant_content:
        try:
            add_to_memory(user_content, assistant_content)
            print("🧠 [MEMORY] Interaction successfully embedded (768 dims).")
        except Exception as e:
            print(f"❌ Storage Error: {e}")
            
    return {"messages": [response]}

def router(state):
    text = state["messages"][-1].content.lower()
    if any(word in text for word in ["code", "repo", "file", "project", "function", "bug"]):
        return "repo_search"
    return "personal_search"