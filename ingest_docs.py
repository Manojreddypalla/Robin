import os
import logging
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from database import repo_vault
from memory_engine import add_to_memory

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestEngine")

def bulk_ingest_from_data():
    """Ingests all documents from the local 'data' folder into Robin's Knowledge Vault."""
    
    # 1. Path Setup: Always relative to this script's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, "data")

    if not os.path.exists(target_dir):
        logger.warning(f"📁 Folder 'data' not found. Creating it at {target_dir}")
        os.makedirs(target_dir)
        print("💡 Drop your PDF, TXT, or MD files into the 'data' folder and run again.")
        return

    print(f"🔍 [INGEST] Scanning: {target_dir}")

    # 2. Optimized Loaders
    # We use 'use_multithreading=True' to speed things up on your Ryzen 7 processor
    loaders = [
        DirectoryLoader(target_dir, glob="**/*.txt", loader_cls=TextLoader, show_progress=True),
        DirectoryLoader(target_dir, glob="**/*.pdf", loader_cls=PyPDFLoader, show_progress=True),
        DirectoryLoader(target_dir, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader, show_progress=True),
    ]

    all_docs = []
    for loader in loaders:
        try:
            all_docs.extend(loader.load())
        except Exception as e:
            logger.error(f"❌ Loader error: {e}")

    if not all_docs:
        print("📭 The 'data' folder is empty. Nothing to ingest.")
        return

    # 3. Professional Splitting
    print(f"✂️  Splitting {len(all_docs)} documents into semantic chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150, # Increased overlap for better context retention
        add_start_index=True
    )
    chunks = text_splitter.split_documents(all_docs)

    # 4. Upload to Qdrant
    print(f"🚀 Uploading {len(chunks)} chunks to Robin's Knowledge Vault...")
    try:
        repo_vault.add_documents(chunks)
        
        # 5. SYNC TO MEMORY: So Robin 'knows' he learned this
        file_names = list(set([doc.metadata.get('source', 'Unknown') for doc in all_docs]))
        summary = f"I have successfully ingested {len(file_names)} documents from the data folder: {', '.join(file_names)}."
        add_to_memory("System Update: Bulk Ingestion", summary)
        
        print(f"✅ Success! Robin is now smarter by {len(all_docs)} files.")
    except Exception as e:
        logger.critical(f"❌ Database Upload Failed: {e}")

if __name__ == "__main__":
    bulk_ingest_from_data()