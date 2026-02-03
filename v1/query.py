import os
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate
from qdrant_client import QdrantClient

# --- Setup ---
COLLECTION_NAME = "robin_knowledge"
USE_CLOUD = False  # Set to True to use Gemini

# 1. Initialize Embeddings (Must match ingest.py)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# 2. Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")
vector_store = QdrantVectorStore(
    client=client, 
    collection_name=COLLECTION_NAME, 
    embeddings=embeddings
)

# 3. Select the "Mind"
if USE_CLOUD:
    # Requires GOOGLE_API_KEY in environment
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
else:
    # Local Llama 3
    llm = ChatOllama(model="llama3", temperature=0)

# 4. Define Robin's Personality (The System Prompt)
template = """
You are Robin, an expert AI code archaeologist. 
Use the following retrieved code snippets to answer the user's question.
If the answer isn't in the code, say you don't know—don't hallucinate.

CONTEXT:
{context}

QUESTION: 
{question}

ROBIN'S RESPONSE:
"""
prompt = ChatPromptTemplate.from_template(template)

# --- The Query Loop ---
def ask_robin(query):
    # Search Qdrant for top 5 relevant chunks
    docs = vector_store.similarity_search(query, k=5)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Generate Answer
    chain = prompt | llm
    response = chain.invoke({"context": context, "question": query})
    
    return response.content

if __name__ == "__main__":
    user_query = input("📖 Ask Robin about the repo: ")
    print("\n" + ask_robin(user_query))