import streamlit as st
import stat, os, shutil
from git import Repo
from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from database import repo_vault
from graph import robin_app
from memory_engine import mem_client # IMPORTED TO SYNC MEMORY

if "messages" not in st.session_state:
    st.session_state.messages = []

def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

st.set_page_config(page_title="ROBIN", page_icon="🚢", layout="wide")
st.title("🚢 ROBIN: AI Archaeologist Dashboard")

with st.sidebar:
    st.header("🧠 Model Selection")
    choice_label = st.radio("Choose Brain:", ["Llama 3 (Local)", "Gemini (Cloud)"], key="brain_select")
    model_id = "1" if "Llama" in choice_label else "2"

    st.divider()
    st.header("📂 Data Ingestion")
    
    # GitHub Ingestion
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
            
            # Update Personal Memory about the new Repo
            mem_client.add(f"I have indexed the GitHub repository: {repo_url}. It contains {len(all_docs)} files.", user_id="manoj_palla")
            
            shutil.rmtree(temp_dir, onerror=remove_readonly)
            status.update(label="✅ Repo Indexed in Vault & Memory!", state="complete")

    st.divider()
    
    # Local File Ingestion
    st.subheader("Local Documents")
    uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True)
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
                repo_vault.add_documents(chunks) # Adds to Qdrant robin_knowledge
                
                # SYNC TO MEM0: Tell Robin Manoj uploaded these specific files
                for doc in all_docs:
                    source_name = doc.metadata.get('source', 'Unknown')
                    mem_client.add(f"Manoj uploaded a document named {source_name}. It contains information regarding {doc.page_content[:200]}...", user_id="manoj_palla")
                
                status.update(label="✅ Memory & Vault Updated!", state="complete")

# --- CHAT DISPLAY & LOGIC ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask Robin..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("🚢 Robin is navigating the vaults...", expanded=True) as status:
            result = robin_app.invoke({
                "messages": st.session_state.messages, 
                "model_choice": model_id
            })
            ans = result["messages"][-1].content
            status.update(label="✅ Success!", state="complete", expanded=False)
        
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})