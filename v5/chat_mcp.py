import asyncio
import sys
import traceback
import os
import re

from langchain_ollama import ChatOllama
# We keep Google import just in case you switch back later, but it's not used now
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import SystemMessage

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# ---------------- CONFIG ----------------

SERVER_SCRIPT = "mcp_server.py"

# ✅ SET TO LLAMA FOR LOCAL USE
USE_MODEL = "llama" 

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------- MAIN ------------------

async def run_chat_session():

    # 1️⃣ Load LLM
    if USE_MODEL == "llama":
        print("🧠 Loading Mistral (Local)...")
        
        # ✅ EXPLICIT PORT CONFIGURATION
        llm = ChatOllama(
            model="mistral",
            temperature=0,
            base_url="http://localhost:11434" # Connects to standard Ollama port
        )
    else:
        # Fallback for Gemini if you switch USE_MODEL back
        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY missing.")
            return
        print("🧠 Loading Gemini 1.5 Flash...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", 
            google_api_key=GEMINI_API_KEY,
            temperature=0
        )

    # 2️⃣ MCP Connect
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
    )

    print(f"🔌 Connecting to {SERVER_SCRIPT}...")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 3️⃣ Load Tools
                tools = await load_mcp_tools(session)
                print(f"✅ Loaded {len(tools)} tools.")

                # 4️⃣ Create Agent
                agent = create_react_agent(llm, tools)

                print("\n💬 Robin Ready! (exit to quit)")
                print("-" * 50)
                
                # --- 🧠 DEEP THINKING SYSTEM PROMPT ---
                deep_think_prompt = """
You are Robin, an advanced AI Agent with Deep Thinking capabilities.

PROTOCOL:
1. You have access to the user's PC and the Web.
2. BEFORE taking any action or answering, you must PLAN inside a <think> block.
3. In the <think> block:
   - Analyze the user's request.
   - Break it down into steps.
   - Decide which tool to use (if any).
4. After the </think> tag, execute the tool or provide the answer.

Example:
User: "Search for Llama 3 news and save it."
Response:
<think>
1. The user wants news about Llama 3.
2. I need to use the 'web_search' tool with query "Llama 3 news".
3. After getting results, I need to use 'write_file' to save them.
</think>
I will search for that now...
"""
                sys_msg = SystemMessage(content=deep_think_prompt)

                while True:
                    try:
                        user_input = input("\nYou: ")
                    except EOFError: break
                    if user_input.lower() in ["exit", "quit"]: break

                    messages = [sys_msg, ("user", user_input)]

                    try:
                        events = agent.astream(
                            {"messages": messages},
                            stream_mode="values"
                        )

                        async for event in events:
                            message = event["messages"][-1]
                            
                            if message.type == "ai":
                                # Show Thinking (Tools)
                                if message.tool_calls:
                                    for tool in message.tool_calls:
                                        print(f"\n⚙️ TOOL: {tool['name']} ({tool.get('args')})")
                                
                                # Show Content (Text + Thoughts)
                                elif message.content:
                                    content = message.content
                                    
                                    # Handle List format (Just in case)
                                    if isinstance(content, list):
                                        text = ""
                                        for block in content:
                                            if isinstance(block, dict) and block.get("type") == "text":
                                                text += block.get("text", "")
                                            elif isinstance(block, str):
                                                text += block
                                        content = text

                                    # Extract <think> blocks for pretty printing
                                    if "<think>" in content:
                                        parts = re.split(r'(<think>.*?</think>)', content, flags=re.DOTALL)
                                        for part in parts:
                                            if part.startswith("<think>"):
                                                # Print thoughts in a different color/style
                                                thought_content = part.replace("<think>", "").replace("</think>", "").strip()
                                                print(f"\n🧠 THINKING:\n{thought_content}\n")
                                            elif part.strip():
                                                print(f"🤖 Robin: {part.strip()}")
                                    else:
                                        print(f"\n🤖 Robin: {content}")

                    except Exception as e:
                        print(f"❌ Error: {e}")
                        traceback.print_exc()

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_chat_session())