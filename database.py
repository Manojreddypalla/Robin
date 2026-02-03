from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from config import QDRANT_URL, REPO_COLLECTION

embeddings = OllamaEmbeddings(model="nomic-embed-text")
client = QdrantClient(url=QDRANT_URL)

repo_vault = QdrantVectorStore(
    client=client, 
    collection_name=REPO_COLLECTION, 
    embedding=embeddings
)