
# config.py
USER_ID = "manoj_palla"
QDRANT_URL = "http://127.0.0.1:6333"
REPO_COLLECTION = "robin_knowledge"
MEM_COLLECTION = "robin_memories"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

from typing import Annotated, TypedDict, List
from langgraph.graph.message import add_messages

# Get your key from Google AI Studio
GEMINI_API_KEY = "AIzaSyAO0vydQscKNNUEzkhPjD7yhZn_n58Khts"

class RobinState(TypedDict):
    messages: Annotated[List, add_messages]
    context: str
    model_choice: str

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
            "ollama_base_url": OLLAMA_BASE_URL
        }
    }
}