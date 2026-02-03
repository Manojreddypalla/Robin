import os
from gitingest import ingest
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore

REPO_URL=input("Enter the Git repository URL: ")
COLLECTION_NAME = "robin_knowledge"

# 2. Extract Code via GitIngest
print("🔍 Ingesting repository...")
summary, tree, content = ingest(REPO_URL)

# 3. Code-Aware Splitting
# Since it's code, we use the Python-specific separators
python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON, 
    chunk_size=1200, 
    chunk_overlap=200
)
docs = python_splitter.create_documents([content])


# 4. Local Embeddings via Ollama
# Make sure you've run 'ollama pull nomic-embed-text'
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# 5. Store in Qdrant
print(f"🚀 Storing {len(docs)} chunks in Qdrant...")
qdrant = QdrantVectorStore.from_documents(
    docs,
    embeddings,
    url="http://localhost:6333",
    collection_name=COLLECTION_NAME,
)

print("✅ Library of Ohara updated!")