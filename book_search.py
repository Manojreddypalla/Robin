# ============================================================
# book_search.py — Enhanced Book Search Node
# ============================================================

import os
import asyncio

from database import book_vault
from config import RobinState

BOOKS_DIR = os.getenv("BOOKS_COPY_DIR", "books")


# ============================================================
# HELPER: Extract pages from PDF using fitz
# ============================================================

def extract_pdf_pages(book_name: str, page_numbers: list) -> str:
    import fitz

    # Try direct path first
    pdf_path = os.path.join(BOOKS_DIR, book_name)

    # Walk books/ if not found directly
    if not os.path.exists(pdf_path):
        print(f"   🔍 Searching for '{book_name}' in {BOOKS_DIR}/...")
        for root, _, files in os.walk(BOOKS_DIR):
            for f in files:
                if f == book_name or f == os.path.basename(book_name):
                    pdf_path = os.path.join(root, f)
                    print(f"   📍 Found at: {pdf_path}")
                    break

    if not os.path.exists(pdf_path):
        print(f"   ❌ PDF not found: {book_name}")
        return f"[PDF not found: {book_name}]"

    print(f"   📂 Opening PDF: {pdf_path}")

    try:
        doc        = fitz.open(pdf_path)
        total_pages = len(doc)
        extracted  = []

        # Also extract ±1 surrounding pages for better context
        expanded_pages = set()
        for p in page_numbers:
            expanded_pages.update([p - 1, p, p + 1])

        target_pages = sorted(p for p in expanded_pages if 0 <= p < total_pages)
        print(f"   📄 Extracting pages: {[p+1 for p in target_pages]} / {total_pages} total")

        for page_num in target_pages:
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                extracted.append(f"[Page {page_num + 1}]\n{text}")
                print(f"      ✅ Page {page_num + 1}: {len(text)} chars")
            else:
                print(f"      ⚠️ Page {page_num + 1}: empty")

        doc.close()

        if not extracted:
            return "[No text extracted from pages]"

        return "\n\n".join(extracted)

    except Exception as e:
        print(f"   ❌ PDF parse error: {e}")
        return f"[PDF parse error: {e}]"


# ============================================================
# MAIN: book_search node
# ============================================================

def book_search(state: RobinState):
    query = state["messages"][-1].content
    print("\n📚 [BOOK SEARCH] ══════════════════════════════")
    print(f"   Query: {query}")

    # ──────────────────────────────────────────────────────
    # STEP 1: Vector similarity search
    # ──────────────────────────────────────────────────────
    print("\n   🔎 Step 1: Vector search...")

    vector_context = ""
    books_hit      = {}   # { "filename.pdf": [page_nums] }
    chunk_count    = 0

    try:
        docs = book_vault.similarity_search(query, k=6)
        chunk_count = len(docs)

        if not docs:
            vector_context = "[No vector matches found]"
            print("   ⚠️ No vector matches.")
        else:
            chunks = []
            for d in docs:
                chunks.append(d.page_content)

                meta      = d.metadata or {}
                source    = meta.get("source", "")
                page_num  = meta.get("page", None)
                book_file = os.path.basename(source) if source else None

                if book_file and page_num is not None:
                    books_hit.setdefault(book_file, []).append(int(page_num))

            vector_context = "VECTOR SEARCH CHUNKS:\n\n" + "\n---\n".join(chunks)

            print(f"   ✅ {chunk_count} chunks retrieved")
            print(f"   📚 Books matched: {list(books_hit.keys())}")
            for book, pages in books_hit.items():
                print(f"      • {book} → pages {[p+1 for p in sorted(set(pages))]}")

    except Exception as e:
        vector_context = f"[Vector search failed: {e}]"
        print(f"   ❌ Vector error: {e}")

    # ──────────────────────────────────────────────────────
    # STEP 2: PDF page extraction
    # Opens the actual uploaded PDF and pulls the exact pages
    # ──────────────────────────────────────────────────────
    print("\n   📖 Step 2: PDF page extraction...")

    pdf_context = ""

    if books_hit:
        pdf_parts = []
        for book_file, pages in books_hit.items():
            unique_pages = sorted(set(pages))
            print(f"\n   📘 {book_file}")
            print(f"      Vector hit pages (0-indexed): {unique_pages}")
            print(f"      Display pages (1-indexed):    {[p+1 for p in unique_pages]}")

            extracted = extract_pdf_pages(book_file, unique_pages)
            pdf_parts.append(
                f"SOURCE: {book_file}\n"
                f"PAGES:  {[p+1 for p in unique_pages]}\n\n"
                f"{extracted}"
            )

        pdf_context = "PDF PAGE EXTRACTS:\n\n" + "\n\n" + ("=" * 50) + "\n\n".join(pdf_parts)
        print(f"\n   ✅ PDF extraction complete")
    else:
        pdf_context = "[No PDF pages to extract — no books matched vector search]"
        print("   ⚠️ No books hit — skipping PDF extraction")

    # ──────────────────────────────────────────────────────
    # STEP 3: Merge context for oracle
    # ──────────────────────────────────────────────────────
    print("\n   🔗 Step 3: Merging context...")

    context = f"""LITERATURE CONTEXT
{"=" * 50}

## VECTOR SEARCH ({chunk_count} chunks)
{vector_context}

{"=" * 50}

## PDF PAGE EXTRACTS (raw text from source PDFs)
{pdf_context}
"""

    total_chars = len(context)
    print(f"   ✅ Context ready: {total_chars} chars")
    print("📚 [BOOK SEARCH] ══════════════════════════════\n")

    return {"context": context}