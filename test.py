from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
# Delete the memory collection specifically
client.delete_collection(collection_name="robin_memories")
print("✅ Deleted 'robin_memories'. It will be recreated with the correct 768 dimensions.")