import asyncio
import sys
import os
import re
import traceback
from dotenv import load_dotenv

# LLM
from langchain_google_genai import ChatGoogleGenerativeAI

# Agent / Tools
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import SystemMessage, HumanMessage

# MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------- CONFIG ----------------

load_dotenv()
GEMINI_API_KEY = "AIzaSyBU0PClUHRiXXj7vA6w5SAmto-Jke03hBw"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(BASE_DIR, "mcp_server.py")


# ---------------- MAIN ----------------

async def run_chat_session():

    # ---------------- LLM INIT ----------------
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY missing in .env")
        return

    print("🧠 Loading Gemini 2.5 Flash...")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0
    )

    # ---------------- MCP SERVER CONFIG ----------------
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=os.environ.copy()
    )

    print(f"🔌 Connecting to MCP Server: {SERVER_SCRIPT}...")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                await session.initialize()
                tools = await load_mcp_tools(session)

                print(f"✅ Loaded {len(tools)} MCP tools.")

                # ---------------- SYSTEM PROMPT ----------------
                system_text = """
You are Robin, an advanced AI Agent.

RULES:
1. You have access to tools.
2. Use tools when needed.
3. Be precise and structured.
4. Do not hallucinate tool results.
"""

                # Create agent
                agent = create_react_agent(
                    llm,
                    tools,
                    prompt=system_text
                )

                chat_history = [SystemMessage(content=system_text)]

                print("\n💬 Robin Ready! (type 'exit' or 'quit' to stop)")
                print("-" * 50)

                # ---------------- CHAT LOOP ----------------
                while True:

                    try:
                        user_input = input("\nYou: ")
                    except EOFError:
                        break

                    if user_input.lower() in ["exit", "quit"]:
                        break

                    chat_history.append(HumanMessage(content=user_input))

                    try:
                        events = agent.astream(
                            {"messages": chat_history},
                            stream_mode="values"
                        )

                        async for event in events:

                            # IMPORTANT: Always replace state
                            chat_history = event["messages"]
                            message = chat_history[-1]

                            if message.type == "ai":

                                # Tool Calls
                                if message.tool_calls:
                                    for tool in message.tool_calls:
                                        print(f"\n⚙️ TOOL CALL → {tool['name']}")
                                        print(f"   Args: {tool.get('args')}")

                                # Normal Response
                                elif message.content:
                                    content = message.content

                                    # Gemini sometimes returns list blocks
                                    if isinstance(content, list):
                                        text = ""
                                        for block in content:
                                            if isinstance(block, dict):
                                                text += block.get("text", "")
                                            elif isinstance(block, str):
                                                text += block
                                        content = text

                                    print(f"\n🤖 Robin: {content}")

                    except Exception as e:
                        print(f"\n❌ Generation Error: {e}")
                        traceback.print_exc()

    except Exception as e:
        print("\n❌ CRITICAL: MCP Connection Failed.")
        print(f"Detail: {e}")
        print("Tip: Check mcp_server.py for runtime errors.")


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":

    # Windows asyncio fix
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_chat_session())
