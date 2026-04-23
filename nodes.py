# ============================================================
# nodes.py — Robin 2.0
# ============================================================

import logging
import asyncio

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from database import repo_vault
from memory_engine import search_memory, add_to_memory
from prompts import get_combined_prompt
from config import (
    GEMINI_KEYS, GEMINI_MODEL, RobinState, OLLAMA_BASE_URL,
    ROUTER_MODEL, REWRITE_MODEL, LOCAL_ORACLE_MODEL,
)
from mcp_bridge import call_mcp_agent
from book_search import book_search  # noqa: F401

logging.getLogger("httpx").setLevel(logging.WARNING)

# ============================================================
# MODELS
# ============================================================

router_llm = ChatOllama(
    model=ROUTER_MODEL, temperature=0, num_predict=128,
    base_url=OLLAMA_BASE_URL,
)
rewrite_llm = ChatOllama(
    model=REWRITE_MODEL, temperature=0, num_predict=256,
    base_url=OLLAMA_BASE_URL,
)
local_oracle_llm = ChatOllama(
    model=LOCAL_ORACLE_MODEL, temperature=0.3, num_predict=2048,
    base_url=OLLAMA_BASE_URL,
)

# ============================================================
# GEMINI ROTATION
# ============================================================

current_key_index = 0

def get_current_gemini():
    global current_key_index
    idx = current_key_index % len(GEMINI_KEYS)
    print(f"🔑 [ORACLE → GEMINI] Key #{idx + 1}")
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_KEYS[idx],
        temperature=0.2,
        request_timeout=30,
    )


def _invoke_llm(messages, model_choice: str):
    """
    Shared LLM helper. Falls back to local on any failure.
    FIX #3: Added else branch so unknown model_choice defaults to local.
    """
    global current_key_index
    response = None

    if model_choice == "1":
        print("🧠 [LLM → LOCAL]")
        try:
            response = local_oracle_llm.invoke(messages)
        except Exception as e:
            response = AIMessage(content=f"Local model error: {e}")

    elif model_choice == "2":
        attempts = 0
        while attempts < len(GEMINI_KEYS):
            try:
                response = get_current_gemini().invoke(messages)
                break
            except Exception:
                current_key_index += 1
                attempts += 1
        if not response:
            print("🌪️ All Gemini keys failed → local fallback")
            try:
                response = local_oracle_llm.invoke(messages)
            except Exception as e:
                response = AIMessage(content=f"Fallback error: {e}")

    else:
        # FIX #3: Unknown model_choice — default to local silently
        print(f"⚠️ Unknown model_choice '{model_choice}' → defaulting to local")
        try:
            response = local_oracle_llm.invoke(messages)
        except Exception as e:
            response = AIMessage(content=f"Local model error: {e}")

    return response or AIMessage(content="Error: LLM invocation failed.")


# ============================================================
# ROUTER
# FIX #8: file_context / folder_context now declared in RobinState (config.py)
# ============================================================

def router(state: RobinState):
    file_context   = (state.get("file_context")   or "").strip()
    folder_context = (state.get("folder_context") or "").strip()

    print(f"🧠 [ROUTER] file_context: {len(file_context)} chars")
    print(f"🧠 [ROUTER] folder_context: {len(folder_context)} chars")

    if file_context or folder_context:
        print("🧠 [ROUTER] Attachment → chat")
        return {"choice": "chat"}

    user_input    = state["messages"][-1].content
    system_prompt = """
You are Robin's Dispatcher — intent classifier.

Choose EXACTLY ONE option:

repo_search     → user's own code, debugging their codebase
book_search     → theoretical concepts, AI research, books
personal_search → personal history, memory, past conversations
specialist      → tools, actions, web search, file system operations, news
chat            → general questions, document analysis, file context
oracle          → greetings, general chat, anything else

OUTPUT FORMAT — return ONLY valid JSON, nothing else:

{{"choice":"repo_search"}}
{{"choice":"book_search"}}
{{"choice":"personal_search"}}
{{"choice":"specialist"}}
{{"choice":"chat"}}
{{"choice":"oracle"}}
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}"),
    ])
    chain = prompt | router_llm | JsonOutputParser()

    try:
        result = chain.invoke({"input": user_input})
        choice = result.get("choice", "oracle")
        print(f"🧠 [ROUTER → {ROUTER_MODEL}] {choice}")
        return {"choice": choice}
    except Exception as e:
        print(f"⚠️ Router fallback: {e}")
        return {"choice": "oracle"}


# ============================================================
# QUERY REWRITER
# ============================================================

REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Rewrite the user query to be optimal for vector similarity search. "
               "Return ONLY the rewritten query, no explanation."),
    ("placeholder", "{messages}"),
    ("user", "{input}"),
])

def query_rewriter(state: RobinState):
    user_input   = state["messages"][-1].content
    print(f"🔄 [REWRITE → {REWRITE_MODEL}]")
    chain        = REWRITE_PROMPT | rewrite_llm | StrOutputParser()
    better_query = chain.invoke({
        "messages": state["messages"][:-1],
        "input":    user_input,
    }).strip()
    print(f"✅ Rewritten: {better_query}")
    return {"reasoning": better_query}


# ============================================================
# REPO SEARCH
# ============================================================

def repo_search(state: RobinState):
    query = state.get("reasoning") or state["messages"][-1].content
    print(f"🔍 [REPO SEARCH] {query}")
    try:
        docs    = repo_vault.similarity_search(query, k=4)
        context = "CODEBASE CONTEXT:\n\n" + "\n\n".join(d.page_content for d in docs)
    except Exception as e:
        context = f"Repo search failed: {e}"
    return {"context": context}


# ============================================================
# PERSONAL SEARCH
# ============================================================

def personal_search(state: RobinState):
    query = state["messages"][-1].content
    print("🧠 [MEMORY SEARCH]")
    try:
        mems    = search_memory(query)
        context = "PERSONAL MEMORY:\n\n" + "\n".join(mems)
    except Exception as e:
        context = f"Memory search failed: {e}"
    return {"context": context}


# ============================================================
# SPECIALIST (MCP)
# FIX #1 + #7: Returns ONLY context (no messages).
# graph.py routes specialist → oracle so oracle summarizes the tool output.
# ============================================================

async def specialist_node(state: RobinState):
    print("🔌 [SPECIALIST → MCP]")
    query    = state["messages"][-1].content
    history  = state["messages"][:-1]
    response = await call_mcp_agent(query, history)
    print(f"📡 TOOL RESULT ({len(response)} chars)")

    # Only set context — oracle will generate the final message with Robin's voice
    return {"context": response}


# ============================================================
# CHAT NODE
# FIX #2: History capped at last 6 messages to prevent file context bloat.
# file_context cleared after use by returning it as empty string.
# ============================================================

async def chat_node(state: RobinState):
    print("💬 [CHAT NODE]")

    model_choice   = state.get("model_choice", "1")
    file_context   = (state.get("file_context")   or "").strip()
    folder_context = (state.get("folder_context") or "").strip()

    last_msg = state["messages"][-1]
    user_question = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    if folder_context:
        system_content = "You are a helpful assistant. Answer using the folder contents provided."
        enriched_human = f"{user_question}\n\nFOLDER CONTENTS:\n{folder_context}"
    elif file_context:
        system_content = "You are a helpful assistant. Answer using the file content provided."
        enriched_human = f"{user_question}\n\nFILE CONTENT:\n{file_context}"
    else:
        system_content = "You are a helpful assistant. Answer clearly and directly."
        enriched_human = user_question

    # FIX #2: Cap history at last 6 messages to avoid file context bloat
    history = list(state["messages"][:-1])[-6:]

    messages = (
        [SystemMessage(content=system_content)]
        + history
        + [HumanMessage(content=enriched_human)]
    )

    response = _invoke_llm(messages, model_choice)

    # FIX #2: Clear file contexts after use — one-shot only
    return {
        "messages":      [response],
        "file_context":  "",
        "folder_context": "",
    }


# ============================================================
# ORACLE  (RAG + Robin persona)
# FIX #4: asyncio.create_task with ensure_future fallback
# ============================================================

async def oracle(state: RobinState):
    print("🔮 [ORACLE]")

    context      = state.get("context", "") or ""
    model_choice = state.get("model_choice", "1")
    messages     = [SystemMessage(content=get_combined_prompt(context))] + list(state["messages"])

    response = _invoke_llm(messages, model_choice)

    # FIX #4: Safe async memory save
    try:
        user_msg = state["messages"][-1].content
        ai_msg   = response.content if hasattr(response, "content") else str(response)

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(add_to_memory(user_msg, ai_msg))
        else:
            loop.run_until_complete(add_to_memory(user_msg, ai_msg))

        print("💾 Memory save queued.")
    except Exception as e:
        print(f"⚠️ Memory save failed: {e}")

    return {"messages": [response]}