from qdrant_client import QdrantClient
from config import QDRANT_URL, REPO_COLLECTION, MEM_COLLECTION

client = QdrantClient(url=QDRANT_URL)

for col in [REPO_COLLECTION, MEM_COLLECTION]:
    print(f"🗑️ Removing {col}...")
    try:
        client.delete_collection(collection_name=col)
        print(f"✅ {col} deleted.")
    except Exception as e:
        print(f"⚠️ Could not delete {col}: {e}")

print("\n✨ Database cleared. Run main.py now to recreate them.")