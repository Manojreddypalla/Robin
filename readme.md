

---

# 🧠 Robin 2.0 — AI Archaeologist Agent

![Architecture](https://chatgpt.com/c/architecture.png)

Robin 2.0 is a **multi-agent AI system with persistent memory, vector search, tool execution, and hybrid LLM routing**, designed to act as a personal AI researcher, code archaeologist, and autonomous assistant.

It combines:

- Local LLMs (Llama3, Qwen, Mistral via Ollama)
- Cloud LLM (Gemini with automatic key rotation)
- Vector databases (Qdrant)
- Persistent memory (Mem0 + MongoDB)
- Tool execution (MCP protocol)
- Multi-agent orchestration (LangGraph)

---

# 🚀 Core Features

## 1. Multi-Agent Architecture

Robin is composed of specialized agents:

| Agent | Role |
| --- | --- |
| Router | Classifies intent |
| Query Rewriter | Optimizes queries for vector search |
| Repo Search | Searches code knowledge vault |
| Book Search | Searches literature vault |
| Personal Search | Searches personal memory |
| Specialist | Executes tools via MCP |
| Oracle | Final reasoning and response |

---

## 2. Persistent Memory

Robin remembers:

- Conversations
- Learned facts
- Personal information
- Ingested documents

Using:

- Mem0
- Qdrant vector database
- MongoDB checkpointing

---

## 3. Hybrid Model System

Robin dynamically uses:

Local models (Ollama):

- Llama 3.1 (Oracle)
- Qwen 2.5 (Router, Rewriter, Specialist)
- Mistral (Fallback)

Cloud model:

- Gemini 2.5 Flash (Oracle cloud mode)

Supports:

- Automatic fallback
- Automatic key rotation

---

## 4. Knowledge Vault (RAG System)

Robin has three vector knowledge bases:

```
robin_knowledge   → Code repositories
robin_literature  → Books & research papers
robin_memories    → Personal memory
```

Supports ingestion of:

- PDF
- TXT
- Markdown
- Git repositories

---

## 5. Tool Execution via MCP

Robin can execute real actions using MCP tools:

Available tools:

- File operations
- Web search
- News retrieval
- Text-to-speech
- Directory management

Example:

```
Create files
Search internet
Read code
Speak responses
```

---

# 🏗️ System Architecture

Flow:

```
User Input
   ↓
Router (Qwen)
   ↓
Query Rewriter
   ↓
Specialized Search / Specialist Tool Agent
   ↓
Oracle (Llama3 / Gemini)
   ↓
Response
   ↓
Memory Storage
```

---

# 🧩 Tech Stack

## Core Frameworks

- LangGraph
- LangChain
- MCP Protocol
- Mem0 Memory Engine

## Models

- Ollama (Llama3, Qwen2.5, Mistral)
- Google Gemini

## Databases

- Qdrant (Vector DB)
- MongoDB (Checkpoint memory)

## Tools

- Python
- FastMCP
- PyPDFLoader
- DirectoryLoader

---

# 📂 Project Structure

```
Robin/
│
├── main.py                 # Main chat interface
├── graph.py                # LangGraph workflow
├── nodes.py                # Agent logic
├── prompts.py              # System prompts
├── config.py               # Configuration
│
├── database.py             # Qdrant setup
├── memory_engine.py       # Mem0 integration
│
├── ingest_engine.py       # Repo ingestion
├── ingest_books.py        # Literature ingestion
├── direct_memory_ingest.py # Personal memory ingest
│
├── mcp_bridge.py          # MCP tool bridge
├── mcp_server.py          # MCP tool server
│
└── data/
```

---

# ⚙️ Installation

## 1. Install dependencies

```
pip install langchain langgraph qdrant-client mem0 ollama pymongo feedparser python-dotenv
```

---

## 2. Install and start Ollama

```
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
ollama pull mistral
ollama pull nomic-embed-text
```

Run Ollama:

```
ollama serve
```

---

## 3. Start Qdrant

Docker:

```
docker run -p 6333:6333 qdrant/qdrant
```

---

## 4. Start MongoDB

```
mongod
```

---

# ▶️ Running Robin

```
python main.py
```

Choose model:

```
[1] Local Llama3
[2] Gemini Cloud
```

---

# 📚 Ingest Knowledge

## Ingest code

```
python ingest_engine.py
```

## Ingest books

```
python ingest_books.py
```

## Ingest personal memory

```
python direct_memory_ingest.py
```

---

# 🔧 MCP Tool Usage Examples

Example commands Robin can execute:

```
Create file hello.txt
Search latest AI news
Read directory contents
Speak hello world
```

---

# 🧠 Memory System

Robin automatically remembers:

```
User facts
Technical discussions
Learned knowledge
Personal context
```

Stored in:

```
Qdrant + Mem0
MongoDB checkpoints
```

---

# ⚡ Performance Features

- GPU accelerated inference (RTX 4060)
- Fully local inference capability
- Cloud fallback support
- Persistent conversational memory
- Async streaming responses

---

# 🎯 Use Cases

Robin can act as:

- AI Research Assistant
- Codebase Analyst
- Personal Knowledge Assistant
- Autonomous Agent
- DevOps assistant
- Learning mentor

---

# 🔮 Future Improvements

Planned features:

- Web UI
- Autonomous task planning
- Multi-agent collaboration
- Vision support
- Autonomous coding

---

# 👤 Author

Manoj Reddy Palla

AI Engineer | Systems Developer | Research-Focused Builder
