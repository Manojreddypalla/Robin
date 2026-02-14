import os
import shutil
import subprocess
import uuid
import tempfile
import logging
from typing import Annotated, Literal, TypedDict, List

# --- Third Party Integrations ---
import git
from pypdf import PdfReader
from docx import Document

# --- LangChain / LangGraph ---
from langchain_core.messages import (
    HumanMessage, SystemMessage, BaseMessage
)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver 
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

# --- Mem0 (The Memory Core) ---
from mem0 import Memory

# ==============================================================================
# 1. CONFIGURATION & SETUP
# ==============================================================================

# Reduce log noise
logging.basicConfig(level=logging.ERROR)

print("\n>>> INITIALIZING ROBIN V3 (Autonomous Agent)...")

# --- DATABASE CONNECTION (FIXED AUTH) ---
# We added '?authSource=admin' which is required for most local Mongo setups
MONGO_URI = "mongodb://admin:admin@localhost:27017/?authSource=admin"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_client.admin.command('ping') 
    print(" [OK] MongoDB Connected (History Saved).")
except Exception as e:
    print(f" [WARNING] MongoDB Auth Failed: {e}")
    print(" Switching to RAM (History lost on exit).")
    mongo_client = None

# --- MEMORY CONFIGURATION (FULLY LOCAL) ---
# We explicitly tell Mem0 to use Ollama for everything to avoid OpenAI errors.
mem0_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {"host": "localhost", "port": 6333}
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password"  # <--- Verify this matches your Neo4j Docker logs
        }
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1",
            "temperature": 0
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text" # Ensure you ran: ollama pull nomic-embed-text
        }
    }
}

try:
    memory_client = Memory.from_config(mem0_config)
    print(" [OK] Neural Memory Core (Mem0) Connected.")
except Exception as e:
    print(f" [WARNING] Memory Core failed: {e}")
    print(" Running in 'Amnesia Mode' (No Long-Term Memory).")
    memory_client = None

# ==============================================================================
# 2. TOOL DEFINITIONS
# ==============================================================================

def _read_file_content(filepath: str) -> str:
    """Helper to read various file formats."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(filepath)
            text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
            return text if text else "[Empty PDF]"
        elif ext in [".docx", ".doc"]:
            doc = Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
    except Exception as e:
        return f"[Error reading file]: {str(e)}"

@tool
def ingest_git_repo(repo_url: str) -> str:
    """Clones a Git repository, reads all code files, and indexes them into 'Project' memory."""
    if not memory_client: return "Memory Core is offline."
    
    try:
        temp_dir = tempfile.mkdtemp()
        print(f"   [System] Cloning {repo_url}...")
        git.Repo.clone_from(repo_url, temp_dir)
        
        file_count = 0
        for root, _, files in os.walk(temp_dir):
            if ".git" in root: continue
            
            for file in files:
                if file.endswith((".py", ".js", ".ts", ".md", ".java", ".cpp", ".html", ".css", ".json")):
                    filepath = os.path.join(root, file)
                    content = _read_file_content(filepath)
                    
                    memory_client.add(
                        f"Repo: {repo_url}\nFile: {file}\nContent:\n{content}",
                        user_id="namespace_project",
                        metadata={"source": "git_repo", "url": repo_url, "filename": file}
                    )
                    file_count += 1
        
        shutil.rmtree(temp_dir)
        return f"Successfully ingested {file_count} files from {repo_url} into Project Memory."
    except Exception as e:
        return f"Git Ingestion Failed: {str(e)}"

@tool
def ingest_local_file(filepath: str, category: Literal["personal", "project"]) -> str:
    """Ingests a local file (PDF, DOCX, TXT). YOU must decide the category."""
    if not memory_client: return "Memory Core is offline."
    if not os.path.exists(filepath): return f"File '{filepath}' not found."
    
    content = _read_file_content(filepath)
    target_id = "namespace_personal" if category == "personal" else "namespace_project"
    
    try:
        memory_client.add(
            f"File: {os.path.basename(filepath)}\nContent:\n{content}",
            user_id=target_id,
            metadata={"source": "local_file", "filename": filepath, "category": category}
        )
        return f"File saved to {category.upper()} memory namespace."
    except Exception as e:
        return f"Memory Save Error: {str(e)}"

@tool
def search_memory(query: str, category: Literal["personal", "project"]) -> str:
    """Searches long-term memory. YOU must decide which DB to search."""
    if not memory_client: return "Memory Core is offline."
    
    target_id = "namespace_personal" if category == "personal" else "namespace_project"
    try:
        results = memory_client.search(query, user_id=target_id, limit=5)
        if not results: return f"No info found in {category} memory."
        
        return "\n".join([f"- {r['memory']}" for r in results])
    except Exception as e:
        return f"Search Error: {str(e)}"

@tool
def execute_system_cmd(command: str) -> str:
    """Executes a Windows shell command. Use for exploration ('dir', 'whoami')."""
    print(f"   [Action] Executing: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout[:1500] 
        return f"Command Error: {result.stderr}"
    except Exception as e:
        return f"Execution Exception: {str(e)}"

tools = [ingest_git_repo, ingest_local_file, search_memory, execute_system_cmd]

# ==============================================================================
# 3. GRAPH ARCHITECTURE
# ==============================================================================

class RobinState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    retry_count: int

llm = ChatOllama(model="llama3.1", temperature=0).bind_tools(tools)
critic_llm = ChatOllama(model="llama3.1", temperature=0) 

def agent_node(state: RobinState):
    response = llm.invoke(state["messages"])
    return {"messages": [response], "retry_count": state.get("retry_count", 0)}

def critic_node(state: RobinState):
    last_msg = state["messages"][-1]
    
    if last_msg.tool_calls or state.get("retry_count", 0) >= 2:
        return {"messages": []}

    prompt = f"""
    REVIEW THIS RESPONSE.
    User Query: {state['messages'][0].content}
    Agent Response: {last_msg.content}
    
    Is this response helpful, accurate, and complete? 
    If YES, output "APPROVE".
    If NO, output "REJECT: <reason>".
    """
    critique = critic_llm.invoke([SystemMessage(content=prompt)])
    
    if critique.content.startswith("REJECT"):
        feedback = f"Critic Feedback: {critique.content}. Please fix this."
        return {"messages": [HumanMessage(content=feedback)], "retry_count": state["retry_count"] + 1}
    
    return {"messages": []}

def router_logic(state: RobinState) -> Literal["tools", "critic", END]:
    last_msg = state["messages"][-1]
    if last_msg.tool_calls: return "tools"
    if isinstance(last_msg, BaseMessage) and not last_msg.tool_calls: return "critic"
    return END

def critic_logic(state: RobinState) -> Literal["agent", END]:
    last_msg = state["messages"][-1]
    if isinstance(last_msg, HumanMessage) and "Critic Feedback" in last_msg.content:
        print(f"   [Critic] Rejected. Retrying (Attempt {state['retry_count']})...")
        return "agent"
    return END

workflow = StateGraph(RobinState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("critic", critic_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router_logic)
workflow.add_edge("tools", "agent") 
workflow.add_conditional_edges("critic", critic_logic)

# ==============================================================================
# 4. MAIN EXECUTION LOOP
# ==============================================================================

def main():
    print("="*50)
    print(" ROBIN V3 - HUMAN-LIKE PERSONAL AGENT")
    print(" Capabilities: Conversational | Memory | Autonomous")
    print("="*50)

    # Session Setup
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    # --- NEW PERSONALITY PROMPT ---
    system_prompt = SystemMessage(content="""
    You are Robin, a warm, witty, and highly intelligent personal assistant.
    
    YOUR CORE BEHAVIOR:
    1. **Be Human-Like**: Speak naturally. Don't be robotic. If the user says "Hello", just say "Hi! How can I help you today?" Do NOT check your memory for "Hello".
    2. **Abstract the Tech**: Never mention "vector databases", "embeddings", or "tools" to the user. If a tool fails, just say "I had a bit of trouble finding that info."
    3. **Autonomy with Judgment**: 
       - ONLY use `search_memory` if the user asks for specific facts (e.g., "What did I work on yesterday?", "Where are my keys?").
       - ONLY use `ingest_` tools if the user explicitly gives you a file or URL.
       - For general questions (e.g., "Why is the sky blue?"), just answer using your own knowledge.
    
    YOUR MEMORY RULES:
    - Personal details go to `namespace_personal`.
    - Work/Code details go to `namespace_project`.
    """)

    # --- DATABASE CONNECTION (SAME AS BEFORE) ---
    checkpointer = None
    if mongo_client:
        try:
            # Quick check if auth works
            checkpointer = MongoDBSaver(mongo_client)
            checkpointer.checkpoint_collection.find_one()
        except Exception:
            checkpointer = None
            
    if not checkpointer:
        print(" [INFO] Using RAM for Short-Term History.")
        checkpointer = MemorySaver()

    app = workflow.compile(checkpointer=checkpointer)
    print(f"\nRobin is Online. Session: {session_id}")

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Robin: Goodbye! Have a great day.")
                break

            inputs = {"messages": [system_prompt, HumanMessage(content=user_input)], "retry_count": 0}
            
            # Stream Events
            for event in app.stream(inputs, config=config):
                for key, value in event.items():
                    if key == "agent":
                        msg = value["messages"][-1]
                        if msg.tool_calls:
                            # Hide the "Decided to call" log from the user to make it feel more seamless
                            # We only print it for your debugging, or you can comment this out:
                            print(f"   (Robin is checking {msg.tool_calls[0]['name']}...)")
            
            # Get Final Response
            snapshot = checkpointer.get(config)
            if snapshot and 'channel_values' in snapshot and snapshot['channel_values']['messages']:
                final_msg = snapshot['channel_values']['messages'][-1]
                if not isinstance(final_msg, HumanMessage):
                    print(f"Robin: {final_msg.content}")

        except KeyboardInterrupt:
            print("\nRobin: Interrupted.")
            break
        except Exception as e:
            print(f" [CRITICAL ERROR] {e}")

if __name__ == "__main__":
    main()