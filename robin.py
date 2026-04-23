from mem0 import Memory

config = {
    "version": "v1.1",

    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434",
            "embedding_dims": 768
        }
    },

    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen2.5:7b",
            "ollama_base_url": "http://localhost:11434",
            "temperature": 0
        }
    },

    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password"
        }
    }
}

mem = Memory.from_config(config)

mem.add(
    messages=[
        {"role": "user", "content": "My name is Manoj and I live in Hyderabad"},
        {"role": "assistant", "content": "Okay Manoj, you live in Hyderabad"}
    ],
    user_id="test_user"
)
print("Done")