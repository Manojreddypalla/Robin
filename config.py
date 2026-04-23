import os
import logging
from typing import Annotated, TypedDict, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 👤 USER IDENTITY
# ============================================================
USER_ID        = os.getenv("USER_ID",        "user")
USER_NAME      = os.getenv("USER_NAME",      "User")
USER_COLLEGE   = os.getenv("USER_COLLEGE",   "")
USER_GRAD_YEAR = os.getenv("USER_GRAD_YEAR", "")
USER_INTERESTS = os.getenv("USER_INTERESTS", "")
USER_VISION    = os.getenv("USER_VISION",    "")
USER_STACK     = os.getenv("USER_STACK",     "")

# ============================================================
# 🤖 ROBIN PERSONALITY
# ============================================================
ROBIN_NAME         = os.getenv("ROBIN_NAME",         "Robin")
ROBIN_ROLE         = os.getenv("ROBIN_ROLE",         "personal AI agent")
ROBIN_PERSONALITY  = os.getenv("ROBIN_PERSONALITY",  "Direct. Warm but focused.")
ROBIN_MENTOR_AREAS = os.getenv("ROBIN_MENTOR_AREAS", "AI/ML, engineering")

# ============================================================
# 🔑 GEMINI KEY ROTATION
# ============================================================
_raw        = os.getenv("GEMINI_KEYS", "")
GEMINI_KEYS = [k.strip() for k in _raw.split(",") if k.strip()]
current_key_index = 0

# ============================================================
# 🏗️ INFRASTRUCTURE
# ============================================================
QDRANT_URL      = os.getenv("QDRANT_URL",      "http://127.0.0.1:6333")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MONGO_URI       = os.getenv("MONGO_URI",       "mongodb://localhost:27017")

# ============================================================
# 📂 COLLECTIONS
# ============================================================
REPO_COLLECTION = os.getenv("REPO_COLLECTION", "robin_knowledge")
BOOK_COLLECTION = os.getenv("BOOK_COLLECTION", "robin_literature")
MEM_COLLECTION  = os.getenv("MEM_COLLECTION",  "robin_memories")

# ============================================================
# 🧠 MODEL NAMES
# ============================================================
ROUTER_MODEL       = os.getenv("ROUTER_MODEL",       "qwen2.5:7b")
REWRITE_MODEL      = os.getenv("REWRITE_MODEL",       "qwen2.5:7b")
LOCAL_ORACLE_MODEL = os.getenv("LOCAL_ORACLE_MODEL",  "llama3.1:8b")
GEMINI_MODEL       = os.getenv("GEMINI_MODEL",        "gemini-2.5-flash")
EMBED_MODEL        = os.getenv("EMBED_MODEL",         "nomic-embed-text")
MEMORY_LLM_MODEL   = os.getenv("MEMORY_LLM_MODEL",   "qwen2.5:7b")

# ============================================================
# 🗄️ NEO4J
# ============================================================
NEO4J_URL      = os.getenv("NEO4J_URL",      "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ============================================================
# 🧠 MEMORY CONFIG
# ============================================================
MEMORY_CONFIG = {
    "version": "v1.1",

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
            "model": EMBED_MODEL,
            "ollama_base_url": OLLAMA_BASE_URL
        }
    },

    "llm": {
        "provider": "ollama",
        "config": {
            "model": MEMORY_LLM_MODEL,
            "ollama_base_url": OLLAMA_BASE_URL,
            "temperature": 0
        }
    },

    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": NEO4J_URL,
            "username": NEO4J_USERNAME,
            "password": NEO4J_PASSWORD
        }
    }
}

# ============================================================
# 🧠 STATE DEFINITION
# ── FIX: file_context and folder_context are declared here
#    so LangGraph persists them in the checkpointer and all
#    nodes (especially the router) can read them from state.
# ============================================================
class RobinState(TypedDict, total=False):
    messages:      Annotated[List[BaseMessage], add_messages]
    context:       Optional[str]
    model_choice:  Optional[str]
    choice:        Optional[str]
    reasoning:     Optional[str]
    target_node:   Optional[str]
    file_context:   Optional[str]    # ← ADD THIS
    folder_context: Optional[str]   # ← ADD THIS

    # ── Attachment contexts injected by app.py ──────────────
    # Single uploaded file — full parsed text (PDF, code, CSV…)
    # Set as a top-level graph input so the router sees it
    # before any LLM classification runs.
    file_context:   Optional[str]

    # Uploaded folder (zip) — all readable files flattened:
    # "### File: path/to/file.py\n```\n<content>\n```\n\n..."
    # Same as above — must be a top-level input, not metadata.
    folder_context: Optional[str]