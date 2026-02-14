from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient, models
from config import REPO_COLLECTION, MEM_COLLECTION, QDRANT_URL, OLLAMA_BASE_URL

print("🔌 Connecting to Database...")

# 1. Initialize Embeddings
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=OLLAMA_BASE_URL
)

# 2. Connect to Qdrant Client (Admin Access)
client = QdrantClient(url=QDRANT_URL)

# 3. HELPER: Auto-Create Collection
def ensure_collection_exists(collection_name, vector_size=768):
    """Checks if a collection exists. If not, creates it."""
    try:
        if not client.collection_exists(collection_name):
            print(f"⚠️ Collection '{collection_name}' missing. Creating...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            print(f"✅ Created '{collection_name}'.")
        else:
            print(f"✅ Collection '{collection_name}' ready.")
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        print("💡 Is Docker running? (docker start qdrant)")

# 4. Run Checks
ensure_collection_exists(REPO_COLLECTION, vector_size=768)
# We don't check MEM_COLLECTION here because Mem0 handles its own init, 
# but checking it doesn't hurt.
ensure_collection_exists(MEM_COLLECTION, vector_size=768)

# 5. Initialize The Vault (Used by nodes.py)
repo_vault = QdrantVectorStore(
    client=client,
    collection_name=REPO_COLLECTION,
    embedding=embeddings,
)