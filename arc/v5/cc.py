import asyncio
import sys
import os
import traceback
from dotenv import load_dotenv

# LLM
from langchain_ollama import ChatOllama

# Agent / Tools
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import SystemMessage, HumanMessage

# MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------- CONFIG ----------------

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(BASE_DIR, "mcp_server.py")

# BEST MODEL FOR TOOL CALLING
MODEL_NAME = "qwen2.5:7b"

# alternatives:
# mistral:7b
# mistral-nemo
# llama3.1:8b


# ---------------- SYSTEM PROMPT ----------------

SYSTEM_TEXT = """
You are Robin, an autonomous AI agent with access to tools.

CRITICAL RULES:

1. When tools can solve the task, you MUST call the tool.
2. NEVER explain tools.
3. NEVER show code examples.
4. NEVER describe tools.
5. ALWAYS execute tools directly.

You are an EXECUTOR, not a teacher.
"""


# ---------------- LLM INIT ----------------

def create_llm():

    print(f"🧠 Loading local model: {MODEL_NAME}")

    llm = ChatOllama(
        model=MODEL_NAME,
        temperature=0,
        num_predict=1024,
    )

    return llm


# ---------------- CHAT LOOP ----------------

async def chat_loop(agent):

    chat_history = [
        SystemMessage(content=SYSTEM_TEXT)
    ]

    print("\n💬 Robin Ready! (type 'exit' or 'quit' to stop)")
    print("-" * 50)

    while True:

        try:
            user_input = input("\nYou: ").strip()
        except EOFError:
            break

        if user_input.lower() in ("exit", "quit"):
            print("👋 Shutting down Robin...")
            break

        if not user_input:
            continue

        chat_history.append(
            HumanMessage(content=user_input)
        )

        try:

            async for event in agent.astream(
                {"messages": chat_history},
                stream_mode="values"
            ):

                chat_history = event["messages"]
                message = chat_history[-1]

                if message.type != "ai":
                    continue

                # TOOL CALL DISPLAY
                if message.tool_calls:

                    for tool in message.tool_calls:

                        print(f"\n⚙️ TOOL CALL → {tool['name']}")
                        print(f"   Args: {tool.get('args')}")

                # NORMAL RESPONSE
                elif message.content:

                    content = message.content

                    # handle structured output
                    if isinstance(content, list):

                        content = "".join(
                            block.get("text", "")
                            if isinstance(block, dict)
                            else str(block)
                            for block in content
                        )

                    print(f"\n🤖 Robin: {content}")

        except Exception as e:

            print(f"\n❌ Generation Error: {e}")
            traceback.print_exc()


# ---------------- MAIN ----------------

async def run_chat_session():

    llm = create_llm()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=os.environ.copy()
    )

    print(f"🔌 Connecting to MCP Server: {SERVER_SCRIPT}")

    try:

        async with stdio_client(server_params) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()

                tools = await load_mcp_tools(session)

                print(f"✅ Loaded {len(tools)} MCP tools")

                # CREATE AGENT
                agent = create_react_agent(
                    llm,
                    tools
                )

                await chat_loop(agent)

    except Exception as e:

        print("\n❌ MCP Connection Failed")
        print(e)
        traceback.print_exc()


# ---------------- ENTRY ----------------

if __name__ == "__main__":

    if sys.platform.startswith("win"):

        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )

    asyncio.run(run_chat_session())
