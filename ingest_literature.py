import os
import shutil
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from database import book_vault, embeddings
from config import BOOK_COLLECTION

BOOKS_COPY_DIR = "books"  # your PDF analyzer reads from here


def ingest_books(data_path="data/literature"):
    """
    1. Loads PDFs/TXTs from data/literature
    2. Chunks and ingests into Qdrant (robin_literature)
    3. Copies every file to /books so the PDF analyzer can access them
    """
    # Create source folder if missing
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        print(f"📁 Created: {data_path} — drop your books there!")
        return

    # Ensure books/ copy folder exists
    os.makedirs(BOOKS_COPY_DIR, exist_ok=True)

    print(f"📚 Scanning: {data_path}...")

    # --------------------------------------------------------
    # 1. LOAD
    # --------------------------------------------------------
    loaders = [
        DirectoryLoader(data_path, glob="**/*.pdf", loader_cls=PyPDFLoader),
        DirectoryLoader(data_path, glob="**/*.txt", loader_cls=TextLoader)
    ]

    docs = []
    for loader in loaders:
        docs.extend(loader.load())

    if not docs:
        print("⚠️ No documents found.")
        return

    print(f"📄 {len(docs)} pages loaded. Chunking...")

    # --------------------------------------------------------
    # 2. CHUNK
    # --------------------------------------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    print(f"✂️ {len(chunks)} chunks created.")

    # --------------------------------------------------------
    # 3. INGEST INTO QDRANT
    # --------------------------------------------------------
    print(f"🚀 Syncing to Qdrant → {BOOK_COLLECTION}...")
    book_vault.add_documents(chunks)
    print("✅ Qdrant ingestion complete.")

    # --------------------------------------------------------
    # 4. COPY FILES TO books/ FOLDER
    # Walks data/literature and copies every PDF/TXT to books/
    # Skips files already there (no overwrite unless changed)
    # --------------------------------------------------------
    print(f"📂 Copying files to /{BOOKS_COPY_DIR}...")

    copied  = 0
    skipped = 0

    for root, _, files in os.walk(data_path):
        for filename in files:
            if not filename.lower().endswith((".pdf", ".txt")):
                continue

            src  = os.path.join(root, filename)
            dest = os.path.join(BOOKS_COPY_DIR, filename)

            # Skip if identical file already exists
            if os.path.exists(dest) and os.path.getsize(dest) == os.path.getsize(src):
                skipped += 1
                continue

            shutil.copy2(src, dest)
            print(f"   📄 Copied: {filename}")
            copied += 1

    print(f"📦 {copied} file(s) copied, {skipped} already up to date.")
    print(f"✅ Robin's literature vault and /{BOOKS_COPY_DIR} are in sync.")


if __name__ == "__main__":
    ingest_books()