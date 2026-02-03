# app.py
import streamlit as st
import stat, os, shutil
from git import Repo
from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from database import repo_vault
from graph import robin_app

# --- INITIALIZE SESSION STATE ---
# This must be the first thing after your imports to avoid AttributeErrors
if "messages" not in st.session_state:
    st.session_state.messages = []

def remove_readonly(func, path, _):
    """Fix for WinError 5 on Windows"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

st.set_page_config(page_title="ROBIN", page_icon="🚢", layout="wide")
st.title("🚢 ROBIN: AI Archaeologist Dashboard")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🧠 Model Selection")
    choice_label = st.radio("Choose Brain:", ["Llama 3 (Local)", "Gemini (Cloud)"], key="brain_select")
    model_id = "1" if "Llama" in choice_label else "2"

    st.divider()
    st.header("📂 Data Ingestion")
    
    # Git Repository
    repo_url = st.text_input("GitHub URL:", placeholder="https://github.com/user/repo")
    if st.button("🚀 Ingest Repo"):
        with st.status("📥 Processing Repo...") as status:
            temp_dir = "temp_repo"
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir, onerror=remove_readonly)
            Repo.clone_from(repo_url, temp_dir)
            all_docs = []
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(('.py', '.md', '.txt')):
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as file:
                            all_docs.append(Document(page_content=file.read(), metadata={"source": f}))
            chunks = RecursiveCharacterTextSplitter.from_language(Language.PYTHON, chunk_size=1200).split_documents(all_docs)
            repo_vault.add_documents(chunks)
            shutil.rmtree(temp_dir, onerror=remove_readonly)
            status.update(label="✅ Success!", state="complete")

    st.divider()
    
    # Local Files
    st.subheader("Local Documents")
    uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, key="file_upload_widget")
    if st.button("📥 Process Uploads"):
        if uploaded_files:
            with st.status("📄 Indexing Documents...") as status:
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)
                all_docs = []
                for f in uploaded_files:
                    path = os.path.join(data_dir, f.name)
                    with open(path, "wb") as b: b.write(f.getbuffer())
                    if f.name.endswith(".pdf"):
                        all_docs.extend(PyPDFLoader(path).load())
                    else:
                        all_docs.append(Document(page_content=f.read().decode('utf-8', errors='ignore'), metadata={"source": f.name}))
                chunks = RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(all_docs)
                repo_vault.add_documents(chunks)
                status.update(label="✅ Files Indexed!", state="complete")
            st.success("Indexing finished!")

# --- CHAT DISPLAY ---
# Display existing chat history on every rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT INPUT & LOGIC ---
if prompt := st.chat_input("Ask Robin..."):
    # 1. Display and save user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Assistant response generation
    with st.chat_message("assistant"):
        with st.status("🚢 Robin is navigating the vaults...", expanded=True) as status:
            st.write("🕵️ Routing intent (Technical vs. Personal)...")
            
            # Execute the Graph with the current message history
            result = robin_app.invoke({
                "messages": st.session_state.messages, 
                "model_choice": model_id
            })
            
            st.write("🔍 Accessing Qdrant for context...")
            st.write("🧠 Integrating findings...")
            
            # Extract final answer
            ans = result["messages"][-1].content
            status.update(label="✅ Context retrieved!", state="complete", expanded=False)
        
        # Display and save assistant message
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})