import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from database import repo_vault, embeddings # Reusing your existing setup

def bulk_ingest_folder(folder_name="data"):
    # 1. Path Setup
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, folder_name)

    if not os.path.exists(target_dir):
        print(f"❌ Folder '{folder_name}' not found! Creating it now...")
        os.makedirs(target_dir)
        print(f"📁 Please drop your PDF, TXT, or MD files into the '{folder_name}' folder and run again.")
        return

    print(f"🔍 Scanning '{folder_name}' for documents...")

    # 2. Define Loaders for different file types
    loaders = {
        ".txt": DirectoryLoader(target_dir, glob="**/*.txt", loader_cls=TextLoader),
        ".pdf": DirectoryLoader(target_dir, glob="**/*.pdf", loader_cls=PyPDFLoader),
        ".md":  DirectoryLoader(target_dir, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader),
    }

    all_docs = []
    for ext, loader in loaders.items():
        print(f"📄 Loading {ext} files...")
        try:
            all_docs.extend(loader.load())
        except Exception as e:
            print(f"⚠️ Warning: Could not load {ext} files: {e}")

    if not all_docs:
        print("Empty folder. No data to process.")
        return

    # 3. Split data into chunks
    print(f"✂️ Splitting {len(all_docs)} documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    chunks = text_splitter.split_documents(all_docs)

    # 4. Upload to Qdrant (robin_knowledge)
    print(f"🚀 Uploading {len(chunks)} chunks to Qdrant database...")
    repo_vault.add_documents(chunks)
    
    print(f"✅ Success! Robin now has access to {len(all_docs)} new files.")

if __name__ == "__main__":
    bulk_ingest_folder()