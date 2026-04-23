import os
import logging
from mem0 import Memory
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. DIRECT CONFIG (Local Override)
USER_ID = "manoj_palla"
MEM_COLLECTION = "robin_memories"
QDRANT_URL = "http://127.0.0.1:6333"
OLLAMA_BASE_URL = "http://100.88.108.111:11434"

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
    # ✅ ADDED THIS: Tells Mem0 to use Ollama instead of OpenAI for processing
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3",
            "ollama_base_url": OLLAMA_BASE_URL,
            "temperature": 0
        }
    }
}

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StandaloneIngest")

def run_direct_ingest():
    print(f"🧠 Initializing Direct Connection to {MEM_COLLECTION} via Ollama...")
    try:
        mem_client = Memory.from_config(MEMORY_CONFIG)
    except Exception as e:
        print(f"❌ Failed to initialize Mem0: {e}")
        return
    
    target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "personal_data")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        return

    # 2. Robust Loaders (Handling Windows encoding for manoj.md)
    loaders = [
        DirectoryLoader(target_dir, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}),
        DirectoryLoader(target_dir, glob="**/*.pdf", loader_cls=PyPDFLoader),
        DirectoryLoader(target_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}), 
    ]

    all_docs = []
    for loader in loaders:
        try:
            all_docs.extend(loader.load())
        except Exception as e:
            logger.error(f"❌ Loader error: {e}")

    if not all_docs:
        print("📭 No files found in personal_data.")
        return

    # 3. Process and Sync
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(all_docs)

    print(f"🚀 Syncing {len(chunks)} chunks directly to {MEM_COLLECTION}...")
    
    success_count = 0
    for chunk in chunks:
        # We simplify the content so Mem0 stores it as a clean factual memory
        memory_content = f"Information from {os.path.basename(chunk.metadata.get('source', 'Unknown'))}: {chunk.page_content}"
        
        try:
            # Pushing directly to robin_memories for user manoj_palla
            mem_client.add(memory_content, user_id=USER_ID)
            success_count += 1
            print(f"✅ Chunk {success_count}/{len(chunks)} synced.")
        except Exception as e:
            print(f"❌ Chunk Sync Failed: {e}")

    print(f"🏁 Finished! Successfully pushed {success_count} memories to Robin.")

if __name__ == "__main__":
    run_direct_ingest()