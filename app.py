
import os
import uuid
import asyncio
import threading
import warnings
import shutil
import zipfile
import io

import nest_asyncio
import streamlit as st
from git import Repo

nest_asyncio.apply()
warnings.filterwarnings("ignore")

# ============================================================
# ENV CONFIG
# ============================================================
from dotenv import load_dotenv
load_dotenv()

ROBIN_NAME   = os.getenv("ROBIN_NAME",         "Robin")
APP_VERSION  = os.getenv("APP_VERSION",        "2.0")
USER_NAME    = os.getenv("USER_NAME",          "User")
LOCAL_MODEL  = os.getenv("LOCAL_ORACLE_MODEL", "Llama 3")
GEMINI_MODEL = os.getenv("GEMINI_MODEL",       "Gemini 2.5 Flash")
GPU_NAME     = os.getenv("GPU_NAME",           "Local GPU")
BOOKS_DIR    = os.getenv("BOOKS_COPY_DIR",     "books")

# ============================================================
# UPLOAD TYPE LISTS
# ============================================================
CHAT_UPLOAD_TYPES = ["pdf", "txt", "md", "py", "js", "ts", "json", "yaml",
                     "yml", "toml", "csv", "html", "xml", "rs", "go", "cpp",
                     "c", "java"]

FOLDER_UPLOAD_TYPES = ["zip"]

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".cpp", ".c", ".java", ".go", ".rs",
    ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".html",
    ".xml", ".csv", ".sh", ".env", ".cfg", ".ini",
}

IGNORE_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".venv"}

# ============================================================
# NODE → DISPLAY LABEL MAP
# ============================================================
NODE_LABELS = {
    "router":          ("🧭", "Routing request…"),
    "query_rewriter":  ("✏️",  "Rewriting query for search…"),
    "repo_search":     ("🔍", "Searching codebase vault…"),
    "book_search":     ("📚", "Searching literature + extracting PDF pages…"),
    "personal_search": ("🧠", "Searching personal memory…"),
    "specialist":      ("🔧", "Executing tool…"),
    "chat":            ("💬", "Analysing file / answering directly…"),
    "oracle":          ("🔮", "Generating response…"),
}

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title=f"{ROBIN_NAME} {APP_VERSION} | AI Architect",
    page_icon="🚢",
    layout="wide",
)

st.markdown("""
<style>
div[data-baseweb="select"] > div:first-child {
    border-color: rgba(255,255,255,0.2) !important;
    box-shadow: none !important;
}
div[data-baseweb="select"]:focus-within > div:first-child {
    border-color: rgba(255,255,255,0.5) !important;
    box-shadow: none !important;
}

/* ── Upload bar ── */
.ubar-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 14px;
    margin-bottom: 6px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px;
}
.ubar-wrap [data-testid="stFileUploaderDropzone"] {
    padding: 0 !important;
    min-height: unset !important;
    height: 34px !important;
    width: 148px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    background: rgba(255,255,255,0.06) !important;
    cursor: pointer !important;
    overflow: hidden !important;
    transition: background 0.18s, border-color 0.18s;
}
.ubar-wrap [data-testid="stFileUploaderDropzone"]:hover {
    background: rgba(255,255,255,0.10) !important;
    border-color: rgba(255,255,255,0.32) !important;
}
.ubar-wrap [data-testid="stFileUploaderDropzone"] svg { display: none !important; }
.ubar-wrap [data-testid="stFileUploaderDropzone"] > div {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
    height: 100% !important;
    gap: 5px !important;
    padding: 0 10px !important;
}
.ubar-wrap [data-testid="stFileUploaderDropzone"] small,
.ubar-wrap [data-testid="stFileUploaderDropzone"] p { display: none !important; }
.ubar-wrap [data-testid="stFileUploaderDropzone"] button { display: none !important; }
.ubar-status {
    font-size: 0.80rem;
    color: rgba(255,255,255,0.40);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin: 0;
}
.ubar-status b { color: rgba(255,255,255,0.88); }
.ubar-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #4ade80;
    margin-right: 5px;
    vertical-align: middle;
}
.ubar-wrap [data-testid="stButton"] button {
    padding: 0 !important;
    width: 26px !important; height: 26px !important;
    min-width: unset !important;
    border-radius: 50% !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    background: rgba(255,255,255,0.06) !important;
    font-size: 0.80rem !important;
    color: rgba(255,255,255,0.55) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.ubar-wrap [data-testid="stButton"] button:hover {
    background: rgba(255,80,80,0.20) !important;
    border-color: rgba(255,80,80,0.40) !important;
    color: #fff !important;
}
.ubar-wrap [data-testid="column"] { padding: 0 !important; min-width: unset !important; }
.ubar-wrap [data-testid="stFileUploader"] > label { display: none !important; }
.ubar-wrap [data-testid="stFileUploader"] { margin-bottom: 0 !important; }

/* ── Pipeline steps ── */
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 0.875rem;
    color: rgba(255,255,255,0.75);
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.pipeline-step:last-child { border-bottom: none; }
.pipeline-step .icon  { font-size: 1.05rem; width: 22px; text-align: center; }
.pipeline-step .label { flex: 1; }
.pipeline-step .badge {
    font-size: 0.72rem;
    padding: 1px 7px;
    border-radius: 20px;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.badge-running  { background: rgba(250,180,0,0.18);  color: #facc15; }
.badge-done     { background: rgba(74,222,128,0.15); color: #4ade80; }
.badge-error    { background: rgba(248,113,113,0.15);color: #f87171; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# INIT
# ============================================================

@st.cache_resource
def initialize_robin():
    print(f"\n🚢 [SYSTEM] Initializing {ROBIN_NAME} {APP_VERSION}...")
    from database import repo_vault, book_vault, embeddings
    from graph import robin_app
    from memory_engine import mem_client
    try:
        embeddings.embed_query("ping")
        print("✅ Embeddings: ONLINE")
    except Exception as exc:
        print(f"⚠️ Embeddings: {exc}")
    return repo_vault, book_vault, robin_app, mem_client

repo_vault, book_vault, robin_app, mem_client = initialize_robin()

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "messages":       [],
    "thread_id":      str(uuid.uuid4()),
    "is_generating":  False,
    "stop_event":     threading.Event(),
    "file_context":   "",
    "file_name":      "",
    "folder_context": "",
    "folder_name":    "",
    "folder_files":   0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# CONSTANTS
# ============================================================
MODEL_OPTIONS = {
    f"{GEMINI_MODEL} (Cloud)":             "2",
    f"{LOCAL_MODEL} (Local — {GPU_NAME})": "1",
}
ALLOWED_EXTENSIONS_VAULT = {
    ".py", ".js", ".ts", ".cpp", ".c", ".java", ".go", ".rs",
    ".json", ".yaml", ".yml", ".toml", ".md", ".txt",
}
IGNORE_DIRS_VAULT = {".git", "node_modules", "__pycache__", "dist", "build", ".venv"}


# ============================================================
# PARSERS
# ============================================================
def parse_uploaded_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    raw  = uploaded_file.getvalue()
    MAX_CHARS = 15000

    if name.endswith(".pdf"):
        try:
            import fitz
            doc   = fitz.open(stream=raw, filetype="pdf")
            pages = []
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    pages.append(f"[Page {i+1}]\n{text}")
            doc.close()
            result = "\n\n".join(pages) if pages else "[PDF empty]"
            if len(result) > MAX_CHARS:
                result = result[:MAX_CHARS] + "\n\n[TRUNCATED]"
            print(f"📄 PDF parsed: {len(result)} chars")
            return result
        except Exception as e:
            return f"[PDF error: {e}]"

    try:
        result = raw.decode("utf-8", errors="ignore")
        if len(result) > MAX_CHARS:
            result = result[:MAX_CHARS] + "\n\n[TRUNCATED]"
        return result
    except Exception as e:
        return f"[File error: {e}]"


def parse_uploaded_folder(zip_file) -> tuple:
    raw   = zip_file.getvalue()
    parts = []
    count = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for member in zf.infolist():
                if member.filename.endswith("/"):
                    continue
                path_parts = member.filename.replace("\\", "/").split("/")
                if any(p in IGNORE_DIRS for p in path_parts):
                    continue
                _, ext = os.path.splitext(member.filename.lower())
                if ext not in TEXT_EXTENSIONS:
                    continue
                if member.file_size > 200_000:
                    continue
                try:
                    with zf.open(member) as f:
                        content = f.read().decode("utf-8", errors="ignore")
                    parts.append(f"### File: {member.filename}\n```\n{content}\n```")
                    count += 1
                except Exception:
                    pass
    except zipfile.BadZipFile:
        return "[Error: not a valid zip]", 0
    return "\n\n".join(parts), count


# ============================================================
# VAULT HELPERS
# ============================================================
def _ingest_repo(repo_url: str) -> int:
    from langchain_core.documents import Document
    from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    temp_dir  = os.path.join("repos", repo_name)
    os.makedirs("repos", exist_ok=True)

    if os.path.exists(temp_dir):
        Repo(temp_dir).remotes.origin.pull()
    else:
        Repo.clone_from(repo_url, temp_dir)

    raw_docs = []
    for root, dirs, files in os.walk(temp_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS_VAULT]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ALLOWED_EXTENSIONS_VAULT:
                continue
            fp = os.path.join(root, fname)
            if os.path.getsize(fp) > 200_000:
                continue
            try:
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    raw_docs.append(Document(
                        page_content=fh.read(),
                        metadata={"source": fp, "file_name": fname,
                                  "extension": ext, "type": "repo"},
                    ))
            except OSError:
                pass

    def _splitter(ext):
        if ext == ".py":
            return RecursiveCharacterTextSplitter.from_language(
                Language.PYTHON, chunk_size=1200, chunk_overlap=150)
        if ext in {".js", ".ts"}:
            return RecursiveCharacterTextSplitter.from_language(
                Language.JS, chunk_size=1200, chunk_overlap=150)
        return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    split_docs = []
    for doc in raw_docs:
        split_docs.extend(_splitter(doc.metadata["extension"]).split_documents([doc]))
    if split_docs:
        repo_vault.add_documents(split_docs)
    return len(split_docs)


def _ingest_books(uploaded_files) -> tuple:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    os.makedirs("data/literature", exist_ok=True)
    os.makedirs(BOOKS_DIR, exist_ok=True)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    all_docs = []
    saved    = []

    for f in uploaded_files:
        raw       = f.getvalue()
        lit_path  = os.path.join("data/literature", f.name)
        book_path = os.path.join(BOOKS_DIR, f.name)

        with open(lit_path, "wb") as fh:
            fh.write(raw)

        if not os.path.exists(book_path) or os.path.getsize(book_path) != len(raw):
            shutil.copy2(lit_path, book_path)

        saved.append(f.name)

        if f.name.lower().endswith(".pdf"):
            all_docs.extend(PyPDFLoader(lit_path).load())
        else:
            all_docs.append(Document(
                page_content=raw.decode("utf-8", errors="ignore"),
                metadata={"source": f.name, "type": "literature"},
            ))

    chunks = splitter.split_documents(all_docs)
    if chunks:
        book_vault.add_documents(chunks)
    return len(chunks), saved


# ============================================================
# PIPELINE STEP RENDERER
# ============================================================

def render_pipeline_step(container, icon: str, label: str, badge: str, badge_class: str):
    """Render a single pipeline step row into a streamlit container."""
    container.markdown(
        f"""<div class="pipeline-step">
            <span class="icon">{icon}</span>
            <span class="label">{label}</span>
            <span class="badge {badge_class}">{badge}</span>
        </div>""",
        unsafe_allow_html=True,
    )


# ============================================================
# STREAM HELPER — with live pipeline UI
# ============================================================

async def _stream_robin(
    prompt: str,
    thread_id: str,
    model_id: str,
    file_context: str,
    folder_context: str,
    response_placeholder,
    pipeline_container,
    stop_event: threading.Event,
) -> tuple:
    from langchain_core.messages import HumanMessage

    effective_thread = (
        str(uuid.uuid4()) if (file_context or folder_context) else thread_id
    )
    config    = {"configurable": {"thread_id": effective_thread}}
    full_text = ""
    stopped   = False

    inputs: dict = {
        "messages":      [HumanMessage(content=prompt)],
        "model_choice":  model_id,
        "file_context":  file_context,
        "folder_context": folder_context,
    }

    # Track which nodes have been seen so we render each once
    seen_nodes: dict[str, object] = {}   # node_name → st slot

    async for msg, metadata in robin_app.astream(
        inputs, config=config, stream_mode="messages"
    ):
        if stop_event.is_set():
            stopped = True
            break

        node = metadata.get("langgraph_node", "")

        # ── Render pipeline step (first time we see this node) ──
        if node and node not in seen_nodes and node in NODE_LABELS:
            icon, label = NODE_LABELS[node]
            slot = pipeline_container.empty()
            seen_nodes[node] = slot
            render_pipeline_step(slot, icon, label, "running", "badge-running")

        # ── Stream tokens from response nodes ──
        if node in {"oracle", "specialist", "chat"}:
            chunk = getattr(msg, "content", "") or ""
            if chunk:
                full_text += chunk
                response_placeholder.markdown(full_text + "▌")

            # Mark oracle/chat/specialist as done once tokens start flowing
            if node in seen_nodes and chunk:
                icon, label = NODE_LABELS.get(node, ("✅", node))
                render_pipeline_step(
                    seen_nodes[node], icon, label, "done", "badge-done"
                )

        # ── Mark non-streaming nodes as done once next node fires ──
        prev_nodes = [n for n in seen_nodes if n != node]
        for prev in prev_nodes:
            slot = seen_nodes[prev]
            icon, label = NODE_LABELS.get(prev, ("✅", prev))
            # Re-render as done only if still showing "running"
            # (we use a simple flag stored in seen_nodes value)
            if seen_nodes[prev] is not None:
                render_pipeline_step(slot, icon, label, "done", "badge-done")
                seen_nodes[prev] = None  # mark as finalised

    response_placeholder.markdown(full_text + (" *(stopped)*" if stopped else ""))

    # Mark any remaining running steps as done
    for node, slot in seen_nodes.items():
        if slot is not None:
            icon, label = NODE_LABELS.get(node, ("✅", node))
            render_pipeline_step(slot, icon, label, "done", "badge-done")

    return full_text, stopped


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title(f"🚢 {ROBIN_NAME}")
    st.caption(f"Session: `{st.session_state.thread_id[:8]}`")

    st.subheader("🧠 Neural Engine")
    brain_label = st.radio(
        "Primary Brain:",
        options=list(MODEL_OPTIONS.keys()),
        index=0,
        key="model_selector",
    )
    model_id = MODEL_OPTIONS[brain_label]

    st.divider()
    st.subheader("📂 Vault Ingestion")

    with st.expander("🔗 Codebase (GitHub)", expanded=False):
        repo_url = st.text_input("Git URL", placeholder="https://github.com/user/repo", key="repo_input")
        if st.button("🚀 Ingest Repo", use_container_width=True):
            if not repo_url.strip():
                st.warning("Enter a Git URL first.")
            else:
                with st.status("📥 Cloning…") as s:
                    try:
                        n = _ingest_repo(repo_url.strip())
                        s.update(label=f"✅ {n} chunks indexed", state="complete")
                    except Exception as exc:
                        s.update(label=f"❌ {exc}", state="error")

    with st.expander("📚 Literature & Books", expanded=False):
        book_files = st.file_uploader(
            "Upload PDFs or TXT", accept_multiple_files=True, key="book_upload")
        if st.button("📥 Index Books", use_container_width=True):
            if not book_files:
                st.warning("Upload files first.")
            else:
                with st.status("📚 Processing…") as s:
                    try:
                        n, names = _ingest_books(book_files)
                        s.update(label=f"✅ {len(names)} file(s) — {n} chunks", state="complete")
                        for name in names:
                            st.caption(f"📄 {name}")
                    except Exception as exc:
                        s.update(label=f"❌ {exc}", state="error")

    with st.expander("👤 Personal Context", expanded=False):
        p_files = st.file_uploader(
            "Upload Personal Notes", accept_multiple_files=True, key="personal_upload")
        if st.button("🧠 Sync Memories", use_container_width=True):
            with st.status("🔐 Syncing…") as s:
                try:
                    from ingest_personal_data import run_direct_ingest
                    run_direct_ingest()
                    if p_files:
                        from ingest_personal_files import ingest_p_files
                        ingest_p_files(p_files)
                    s.update(label="✅ Memories synced!", state="complete")
                except Exception as exc:
                    s.update(label=f"❌ {exc}", state="error")

    st.divider()
    with st.expander("🧰 Available Tools", expanded=False):
        st.markdown(
            "- 📂 `list_directory(path)`\n- 📄 `read_file(path)`\n"
            "- ✍️ `write_file(path, content)`\n- 🌍 `web_search(query)`\n"
            "- 📰 `get_latest_news(source)`\n- 🔊 `speak(text)`\n"
            "- 🔍 `search_news(query, days_back)`\n- ⚙️ `run_command(cmd)`"
        )

    st.divider()
    if st.button("🧹 Clear Chat", use_container_width=True):
        for k in ["messages", "file_context", "file_name", "folder_context", "folder_name"]:
            st.session_state[k] = [] if k == "messages" else ""
        st.session_state.folder_files  = 0
        st.session_state.thread_id     = str(uuid.uuid4())
        st.session_state.is_generating = False
        st.session_state.stop_event.clear()
        st.rerun()


# ============================================================
# HEADER
# ============================================================
st.title(f"🚢 {ROBIN_NAME}")
st.caption(f"Engine: **{brain_label}** | User: **{USER_NAME}**")

# ============================================================
# UPLOAD BAR
# ============================================================
st.markdown('<div class="ubar-wrap">', unsafe_allow_html=True)

file_col, folder_col, status_col, clear_col = st.columns(
    [0.16, 0.18, 0.58, 0.08], gap="small"
)

with file_col:
    chat_file = st.file_uploader(
        "📄 File", type=CHAT_UPLOAD_TYPES, key="chat_file_upload",
        label_visibility="collapsed",
        help="PDF, code, markdown, CSV, JSON…",
        disabled=st.session_state.is_generating,
    )

with folder_col:
    chat_folder = st.file_uploader(
        "📁 Folder (.zip)", type=FOLDER_UPLOAD_TYPES, key="chat_folder_upload",
        label_visibility="collapsed",
        help="Zip your folder — all readable files parsed",
        disabled=st.session_state.is_generating,
    )

with status_col:
    badges = []
    if st.session_state.file_name:
        badges.append(f'<span class="ubar-dot"></span><b>{st.session_state.file_name}</b>')
    if st.session_state.folder_name:
        badges.append(
            f'<span class="ubar-dot"></span><b>{st.session_state.folder_name}</b>'
            f' ({st.session_state.folder_files} files)'
        )
    label_html = (
        '<p class="ubar-status">' + " &middot; ".join(badges) + " — sends with next message</p>"
        if badges else '<p class="ubar-status">No attachment</p>'
    )
    st.markdown(label_html, unsafe_allow_html=True)

with clear_col:
    if st.session_state.file_name or st.session_state.folder_name:
        if st.button("✕", key="clear_attachment"):
            for k in ["file_context", "file_name", "folder_context", "folder_name"]:
                st.session_state[k] = ""
            st.session_state.folder_files = 0
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# File parse on attach
if chat_file and chat_file.name != st.session_state.file_name:
    with st.spinner(f"Parsing {chat_file.name}…"):
        parsed = parse_uploaded_file(chat_file)
        st.session_state.file_context   = parsed
        st.session_state.file_name      = chat_file.name
        st.session_state.folder_context = ""
        st.session_state.folder_name    = ""
        st.session_state.folder_files   = 0
    st.rerun()

if chat_folder and chat_folder.name != st.session_state.folder_name:
    with st.spinner(f"Extracting {chat_folder.name}…"):
        folder_str, file_count = parse_uploaded_folder(chat_folder)
        if file_count == 0:
            st.error(folder_str)
        else:
            st.session_state.folder_context = folder_str
            st.session_state.folder_name    = chat_folder.name
            st.session_state.folder_files   = file_count
            st.session_state.file_context   = ""
            st.session_state.file_name      = ""
    st.rerun()

st.divider()

# ============================================================
# CHAT HISTORY
# ============================================================
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🚢"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg.get("file_name"):
            st.caption(f"📄 {msg['file_name']}")
        if msg.get("folder_name"):
            st.caption(f"📁 {msg['folder_name']} ({msg.get('folder_files', 0)} files)")
        st.markdown(msg["content"])

if st.session_state.is_generating:
    if st.button("⏹ Stop generating"):
        st.session_state.stop_event.set()
        st.session_state.is_generating = False

# ============================================================
# CHAT INPUT
# ============================================================
prompt = st.chat_input(
    f"Ask {ROBIN_NAME}…",
    disabled=st.session_state.is_generating,
)

# ============================================================
# SEND MESSAGE
# ============================================================
if prompt:
    st.session_state.stop_event.clear()
    st.session_state.is_generating = True

    file_context   = st.session_state.file_context
    file_name      = st.session_state.file_name
    folder_context = st.session_state.folder_context
    folder_name    = st.session_state.folder_name
    folder_files   = st.session_state.folder_files

    st.session_state.messages.append({
        "role": "user", "content": prompt,
        "file_name": file_name, "folder_name": folder_name, "folder_files": folder_files,
    })

    with st.chat_message("user", avatar="👤"):
        if file_name:
            st.caption(f"📄 {file_name}")
        if folder_name:
            st.caption(f"📁 {folder_name} ({folder_files} files)")
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🚢"):

        # ── Pipeline panel (shows steps as they fire) ──
        with st.expander("⚙️ Pipeline", expanded=True):
            pipeline_container = st.container()

        # ── Response area ──
        response_placeholder = st.empty()

        try:
            loop = asyncio.get_event_loop()
            full_response, was_stopped = loop.run_until_complete(
                _stream_robin(
                    prompt,
                    st.session_state.thread_id,
                    model_id,
                    file_context,
                    folder_context,
                    response_placeholder,
                    pipeline_container,
                    st.session_state.stop_event,
                )
            )

            if was_stopped:
                st.caption("⏹ Stopped by user")

        except Exception as exc:
            full_response = f"❌ Error: {exc}"
            response_placeholder.markdown(full_response)

    st.session_state.is_generating = False
    st.session_state.stop_event.clear()

    # Clear attachments after send
    for k in ["file_context", "file_name", "folder_context", "folder_name"]:
        st.session_state[k] = ""
    st.session_state.folder_files = 0

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
