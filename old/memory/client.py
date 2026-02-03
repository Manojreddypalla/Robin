# memory/client.py

import os
from dotenv import load_dotenv
from mem0 import Memory

load_dotenv()


def get_memory_client():

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    print(f"[MEMORY] Using LLM: {provider}")

    config = {

        # Embeddings
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
            }
        },

        # Vector DB
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": os.getenv("QDRANT_HOST"),
                "port": int(os.getenv("QDRANT_PORT"))
            }
        },

        # Graph DB
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": os.getenv("NEO4J_URL"),
                "username": os.getenv("NEO4J_USER"),
                "password": os.getenv("NEO4J_PASSWORD")
            }
        }
    }

    # Select LLM
    if provider == "gemini":
        config["llm"] = {
            "provider": "gemini",
            "config": {
                "api_key": os.getenv("GEMINI_API_KEY"),
                "model": "gemini-pro"
            }
        }
    else:
        # Ollama (default)
        config["llm"] = {
            "provider": "ollama",
            "config": {
                # No base_url here — mem0 will use default endpoint.
                "model": os.getenv("OLLAMA_CHAT_MODEL", "llama3")
            }
        }

    return Memory.from_config(config)
