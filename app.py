import streamlit as st
import os
import shutil
import uuid
import warnings
import time
from git import Repo

# --- 1. PERFORMANCE CACHING & SELF-HEALING ---
@st.cache_resource
def initialize_robin():
    """Initializes engines once and verifies the embedding model is awake."""
    from database import repo_vault
    from graph import robin_app
    from memory_engine import mem_client
    from database import embeddings # Direct access to test connection
    
    # 🛡️ Self-Healing: Wake up Ollama before starting
    try:
        embeddings.embed_query("ping") 
    except Exception:
        pass # If it fails here, the first call might still be slow, but it won't crash the UI
        
    return repo_vault, robin_app, mem_client

# Load cached engines
repo_vault, robin_app, mem_client = initialize_robin()
warnings.filterwarnings("ignore")

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Robin 2.0", page_icon="🚢", layout="wide")

# --- 3. FORCE VISIBILITY CSS ---
# This ensures your sidebar text is visible regardless of Streamlit theme
st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 350px; max-width: 400px; }
    .st-emotion-cache-16ids9p p { color: #31333F !important; font-weight: 500; } /* Force Sidebar text color */
    .stAppHeader {display: none;}
    .stChatMessage {border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

# --- 4. SESSION MANAGEMENT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

def remove_readonly(func, path, _):
    os.chmod(path, 0o777)
    func(path)

# --- 5. SIDEBAR (FIXED VISIBILITY) ---
with st.sidebar:
    st.title("🚢 Robin 2.0")
    st.info(f"Session ID: {st.session_state.thread_id[:8]}")
    
    st.subheader("🧠 Neural Engine")
    # Using a selectbox instead of radio for better visibility in your UI
    brain_choice = st.selectbox(
        "Choose Brain:",
        ["Gemini 2.5 (Cloud)", "Llama 3 (Local)"],
        index=0
    )
    model_id = "2" if "Gemini" in brain_choice else "1"

    st.divider()

    st.subheader("📂 Knowledge Vault")
    
    # GitHub Loader
    with st.expander("🔗 GitHub Repository", expanded=False):
        repo_url = st.text_input("Git URL", placeholder="https://github.com/...")
        if st.button("🚀 Ingest", use_container_width=True):
            if repo_url:
                with st.status("📥 Cloning...") as status:
                    temp_dir = "temp_repo"
                    if os.path.exists(temp_dir): shutil.rmtree(temp_dir, onerror=remove_readonly)
                    Repo.clone_from(repo_url, temp_dir)
                    
                    from langchain_core.documents import Document
                    from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
                    
                    all_docs = []
                    for root, _, files in os.walk(temp_dir):
                        for f in files:
                            if f.endswith(('.py', '.md', '.txt')):
                                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as file:
                                    all_docs.append(Document(page_content=file.read(), metadata={"source": f}))
                    
                    splitter = RecursiveCharacterTextSplitter.from_language(Language.PYTHON, chunk_size=1200, chunk_overlap=100)
                    repo_vault.add_documents(splitter.split_documents(all_docs))
                    
                    mem_client.add(messages=[{"role": "system", "content": f"Ingested repo: {repo_url}"}], user_id="manoj_palla")
                    shutil.rmtree(temp_dir, onerror=remove_readonly)
                    status.update(label="✅ Repo Synced!", state="complete")

    # File Uploader
    with st.expander("📄 Local Files", expanded=False):
        files = st.file_uploader("PDF/TXT/MD", accept_multiple_files=True)
        if st.button("📥 Process", use_container_width=True):
            if files:
                with st.status("📚 Indexing...") as status:
                    from langchain_community.document_loaders import PyPDFLoader
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                    from langchain_core.documents import Document
                    
                    os.makedirs("data", exist_ok=True)
                    docs = []
                    for f in files:
                        path = os.path.join("data", f.name)
                        with open(path, "wb") as b: b.write(f.getbuffer())
                        if f.name.endswith(".pdf"): docs.extend(PyPDFLoader(path).load())
                        else: docs.append(Document(page_content=f.read().decode('utf-8', errors='ignore'), metadata={"source": f.name}))
                    
                    repo_vault.add_documents(RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(docs))
                    mem_client.add(messages=[{"role": "system", "content": f"Uploaded files: {[f.name for f in files]}"}], user_id="manoj_palla")
                    status.update(label="✅ Documents Indexed!", state="complete")

    st.divider()
    if st.button("🧹 Clear Chat History", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# --- 6. MAIN CHAT ---
st.title("AI Archaeologist")

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🚢"):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask Robin..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🚢"):
        msg_placeholder = st.empty()
        with st.status("🚢 Digging...", expanded=False) as status:
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            
            # 🛡️ Retry Logic for the "dim: 0" error
            attempts = 0
            while attempts < 2:
                try:
                    result = robin_app.invoke({
                        "messages": [("user", prompt)], 
                        "model_choice": model_id
                    }, config=config)
                    ans = result["messages"][-1].content
                    break
                except Exception as e:
                    if "Vector dimension" in str(e) and attempts == 0:
                        time.sleep(2) # Give Ollama a second to wake up
                        attempts += 1
                        continue
                    ans = f"❌ Error: {e}"
                    break
            
            status.update(label="✅ Success!", state="complete")
        
        msg_placeholder.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})