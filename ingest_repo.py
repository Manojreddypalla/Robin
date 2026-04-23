import os
import subprocess
from pathlib import Path
from typing import List

from langchain.schema import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore

# ==============================
# 🔧 CONFIGURATION
# ==============================

REPO_BASE_DIR = Path("repos")
COLLECTION_NAME = "robin_knowledge"

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".cpp", ".c", ".java", ".go", ".rs",
    ".html", ".css",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".txt"
}

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", "dist", "build", ".venv"
}

QDRANT_URL = "http://localhost:6333"
EMBEDDING_MODEL = "nomic-embed-text"


# ==============================
# 📥 GIT HANDLING
# ==============================

def clone_or_update_repo(repo_url: str) -> Path:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = REPO_BASE_DIR / repo_name

    REPO_BASE_DIR.mkdir(exist_ok=True)

    if not repo_path.exists():
        print(f"📥 Cloning {repo_url}...")
        subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)
    else:
        print(f"🔄 Updating {repo_name}...")
        subprocess.run(["git", "-C", str(repo_path), "pull"], check=True)

    return repo_path


# ==============================
# 📂 FILE LOADING
# ==============================

def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def load_documents(repo_path: Path) -> List[Document]:
    documents = []

    for root, _, files in os.walk(repo_path):
        root_path = Path(root)

        if should_ignore(root_path):
            continue

        for file in files:
            file_path = root_path / file
            ext = file_path.suffix.lower()

            if ext not in ALLOWED_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "file_name": file,
                            "extension": ext,
                        },
                    )
                )

            except Exception as e:
                print(f"⚠️ Skipped {file_path}: {e}")

    print(f"📄 Loaded {len(documents)} files")
    return documents


# ==============================
# ✂️ SPLITTING
# ==============================

def get_splitter(extension: str):
    if extension == ".py":
        return RecursiveCharacterTextSplitter.from_language(
            Language.PYTHON, chunk_size=1200, chunk_overlap=200
        )
    elif extension in [".js", ".ts"]:
        return RecursiveCharacterTextSplitter.from_language(
            Language.JS, chunk_size=1200, chunk_overlap=200
        )
    else:
        return RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )


def split_documents(documents: List[Document]) -> List[Document]:
    split_docs = []

    for doc in documents:
        splitter = get_splitter(doc.metadata["extension"])
        chunks = splitter.split_documents([doc])

        split_docs.extend(chunks)

    print(f"✂️ Created {len(split_docs)} chunks")
    return split_docs


# ==============================
# 🧠 VECTOR STORE
# ==============================

def store_in_qdrant(documents: List[Document]):
    print("🧠 Generating embeddings...")

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    print("🚀 Storing in Qdrant...")

    QdrantVectorStore.from_documents(
        documents,
        embeddings,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
    )

    print("✅ Ingestion complete!")


# ==============================
# 🚀 MAIN PIPELINE
# ==============================

def ingest_repository(repo_url: str):
    repo_path = clone_or_update_repo(repo_url)
    documents = load_documents(repo_path)
    split_docs = split_documents(documents)
    store_in_qdrant(split_docs)


# ==============================
# ▶️ ENTRY POINT
# ==============================

if __name__ == "__main__":
    repo_url = input("Enter repository URL: ").strip()
    ingest_repository(repo_url)