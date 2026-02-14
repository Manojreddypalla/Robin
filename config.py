
import os
import logging
from typing import Annotated, TypedDict, List, Literal
from langgraph.graph.message import add_messages
from typing import TypedDict, List, Literal, Annotated
from langgraph.graph.message import add_messages
from typing import Annotated, List, TypedDict, Literal
from langchain_core.messages import BaseMessage # <--- ADD THIS LINE
from langgraph.graph.message import add_messages

# --- USER CONFIG ---
USER_ID = "manoj_palla"

# 🔑 TEAM KEY VAULT
_RAW_KEYS = [
     # Manoj's Key
]

# Clean keys and provide a global index for rotation
GEMINI_KEYS = [k.strip() for k in _RAW_KEYS if k.strip()]
current_key_index = 0  # Global tracker for rotation

# --- INFRASTRUCTURE CONFIG ---
QDRANT_URL = "http://127.0.0.1:6333"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
MONGO_URI = "mongodb://localhost:27017"

# --- COLLECTION NAMES ---
REPO_COLLECTION = "robin_knowledge"
MEM_COLLECTION = "robin_memories"

# --- STATE DEFINITION ---
class RobinState(TypedDict, total=False):
    """
    Final Production State for Robin v2.
    Ensures seamless handoffs between Router, Oracle, and MCP Tools.
    """

    # 1. Core Conversation (History + New Messages)
    # Annotated with add_messages so new responses APPEND rather than OVERWRITE
    messages: Annotated[List[BaseMessage], add_messages]

    # 2. RAG & Memory Context
    # Stores technical/personal data retrieved from Vault/Mem0
    context: str

    # 3. User Preference
    # "1" for Local (Mistral), "2" for Cloud (Gemini)
    model_choice: str

    # 4. Routing Data
    # Stores the target node determined by the Router
    target_node: str

    # 5. Intent Logic
    # Stores the reasoning behind why a specific path was chosen
    reasoning: str

# --- MEM0 CONFIGURATION ---
MEMORY_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": QDRANT_URL,
            "collection_name": MEM_COLLECTION,
            "embedding_model_dims": 768, 
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": OLLAMA_BASE_URL
        }
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3",
            "ollama_base_url": OLLAMA_BASE_URL,
            "temperature": 0
        }
    }
}
