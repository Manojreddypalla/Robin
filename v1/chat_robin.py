import os
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from qdrant_client import QdrantClient

# 1. Setup
embeddings = OllamaEmbeddings(model="nomic-embed-text")
client = QdrantClient(url="http://localhost:6333")
vector_store = QdrantVectorStore(client=client, collection_name="robin_knowledge", embedding=embeddings)

# 2. Initialize LLM (Using Llama 3 locally)
llm = ChatOllama(model="llama3", temperature=0.7)

# 3. Memory for the CURRENT session (We'll move this to Mongo later)
chat_history = []

# 4. Robin's Personality
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Robin, a personal AI archaeologist and developer assistant. "
               "You have access to code repositories and user history. "
               "Use the provided context to answer questions precisely. "
               "If you don't know, just say so."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("system", "CONTEXT FROM REPOSITORY:\n{context}"),
    ("human", "{question}"),
])

def chat():
    print("🚢 Robin: 'Hello Manoj! I'm ready to explore the repositories. Type 'exit' to quit.'")
    
    while True:
        query = input("\n👤 You: ")
        if query.lower() in ["exit", "quit"]:
            break

        # A. Retrieval - Get relevant code
        docs = vector_store.similarity_search(query, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])

        # B. Generation
        chain = prompt | llm
        response = chain.invoke({
            "question": query,
            "chat_history": chat_history,
            "context": context
        })

        # C. Update History (In-memory for now)
        chat_history.append(HumanMessage(content=query))
        chat_history.append(AIMessage(content=response.content))

        print(f"\n🚢 Robin: {response.content}")

if __name__ == "__main__":
    chat()