import asyncio
import sys
import os
import re
import traceback
from dotenv import load_dotenv

# LLMs
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

# Agent / Tools
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# MCP (Using the correct ClientSession)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------------- CONFIGURATION ----------------

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Absolute path to ensure Python finds your server file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(BASE_DIR, "mcp_server.py")

# Choose: "mistral" or "gemini"
USE_MODEL = "mistral" 

# ---------------- MAIN ----------------

async def run_chat_session():

    # 1. Initialize LLM
    if USE_MODEL == "mistral":
        print("🧠 Loading Mistral (Local)...")
        llm = ChatOllama(
            model="mistral",
            temperature=0,
            base_url="http://localhost:11434"
        )
       
    else:
        if not GEMINI_API_KEY:
            print("❌ Error: GEMINI_API_KEY is missing in .env")
            return
        print("🧠 Loading Gemini 2.5 Flash...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0
        )

    # 2. Configure MCP Server Parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=os.environ.copy() # Pass environment variables (API keys)
    )

    print(f"🔌 Connecting to MCP Server: {SERVER_SCRIPT}...")

    # 3. Connection Block
    # The agent and chat loop MUST run inside this block to keep the connection alive
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                # Initialize Connection
                await session.initialize()
                
                # Load Tools Dynamically
                tools = await load_mcp_tools(session)
                print(f"✅ Loaded {len(tools)} MCP tools.")

                # Create the Agent
                agent = create_react_agent(llm, tools)

                # System Prompt
                system_text = """
You are Robin, an advanced AI Agent.

PROTOCOL:
1. You have access to the user's PC and Web via tools.
2. BEFORE acting, plan inside a <think> block.
3. Then execute the tool or answer.

Example:
User: "Search for X"
<think>
I need to use web_search for X.
</think>
I will search now...
"""
                chat_history = [SystemMessage(content=system_text)]

                print("\n💬 Robin Ready! (type 'exit' or 'quit' to stop)")
                print("-" * 50)

                # 4. Chat Loop
                while True:
                    try:
                        user_input = input("\nYou: ")
                    except EOFError:
                        break

                    if user_input.lower() in ["exit", "quit"]:
                        break

                    # Append User Message
                    chat_history.append(HumanMessage(content=user_input))

                    try:
                        # Run Agent Stream
                        events = agent.astream(
                            {"messages": chat_history},
                            stream_mode="values"
                        )

                        async for event in events:
                            message = event["messages"][-1]

                            # Only process AI messages we haven't seen/printed yet
                            # (LangGraph yields the whole state, so we just take the last one if it's new)
                            if message.type == "ai":
                                
                                # A. Handle Tool Calls (Logs)
                                if message.tool_calls:
                                    for tool in message.tool_calls:
                                        print(f"\n⚙️ TOOL: {tool['name']} {tool.get('args')}")
                                
                                # B. Handle Text Content
                                elif message.content:
                                    content = message.content
                                    
                                    # Handle list content (common in some LLM outputs)
                                    if isinstance(content, list):
                                        text = ""
                                        for block in content:
                                            if isinstance(block, dict):
                                                text += block.get("text", "")
                                            elif isinstance(block, str):
                                                text += block
                                        content = text

                                    # Pretty Print Thinking Blocks
                                    if "<think>" in content:
                                        parts = re.split(r'(<think>.*?</think>)', content, flags=re.DOTALL)
                                        for part in parts:
                                            if part.startswith("<think>"):
                                                thought = part.replace("<think>", "").replace("</think>", "").strip()
                                                print(f"\n🧠 THINKING:\n{thought}\n")
                                            elif part.strip():
                                                print(f"🤖 Robin: {part.strip()}")
                                    else:
                                        print(f"\n🤖 Robin: {content}")
                                    
                                    # Important: Update our local history so the next loop has context
                                    # (Ideally, we replace chat_history with event["messages"], 
                                    # but appending works for simple linear chat)
                                    if chat_history[-1] != message:
                                         chat_history.append(message)

                    except Exception as e:
                        print(f"❌ Error during generation: {e}")
                        traceback.print_exc()

    except Exception as e:
        print("\n❌ CRITICAL: MCP Connection Failed.")
        print(f"Detail: {e}")
        print("Tip: Make sure 'pip install uvicorn' is run and 'mcp_server.py' is error-free.")

if __name__ == "__main__":
    # Windows specific fix for asyncio
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(run_chat_session())