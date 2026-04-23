from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient, models
from config import REPO_COLLECTION, BOOK_COLLECTION, MEM_COLLECTION, QDRANT_URL, OLLAMA_BASE_URL

print("🔌 Connecting to Database...")

# 1. Initialize Embeddings
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=OLLAMA_BASE_URL
)

# 2. Connect to Qdrant Client
client = QdrantClient(url=QDRANT_URL)

# 3. HELPER: Auto-Create Collections
def ensure_collection_exists(collection_name, vector_size=768):
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

# 4. Run Checks for all three
ensure_collection_exists(REPO_COLLECTION)
ensure_collection_exists(BOOK_COLLECTION)
ensure_collection_exists(MEM_COLLECTION)

# 5. Initialize the specific Vector Stores
repo_vault = QdrantVectorStore(client=client, collection_name=REPO_COLLECTION, embedding=embeddings)
book_vault = QdrantVectorStore(client=client, collection_name=BOOK_COLLECTION, embedding=embeddings)