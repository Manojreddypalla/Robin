USER_ID = "manoj_palla"
QDRANT_URL = "http://127.0.0.1:6333"
REPO_COLLECTION = "robin_knowledge"
MEM_COLLECTION = "robin_memories"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

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