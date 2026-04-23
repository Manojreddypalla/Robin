# ============================================================
# ROBIN MCP BRIDGE — Persistent Session + Task Chaining
# ============================================================

import asyncio
import sys
import os
import re

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

# ============================================================
# SERVER SETUP
# ============================================================

BASE_DIR      = os.getcwd()
SERVER_SCRIPT = os.path.join(BASE_DIR, "MCP_AGENT", "mcp_server.py")

server_params = StdioServerParameters(
    command=sys.executable,
    args=[SERVER_SCRIPT],
    env=os.environ.copy()
)

# ============================================================
# TOOL REGISTRY
# ============================================================

TOOL_DESCRIPTIONS = """
Available tools:
- list_directory(path)              → list files/folders
- read_file(path)                   → read a file's content
- write_file(path, content)         → write/create a file
- web_search(query)                 → search the internet
- get_latest_news(source)           → get news; source = ai | tech | general | hackernews | security | agritech | science | business
- search_news(query, days_back)     → search news by keyword
- speak(text)                       → speak text aloud
- run_command(command)              → run a shell command
"""

# ============================================================
# LLM TASK PLANNER
# ============================================================

_planner_llm = ChatOllama(model="qwen2.5:7b", temperature=0, num_predict=512)

_PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""You are a task planner for an AI agent.

Given a user request, output an ordered list of tool calls to complete it.
Each step can reference a previous step's output using the placeholder {{step_N_output}}

{TOOL_DESCRIPTIONS}

RULES:
- Output ONLY valid JSON
- steps is an array of objects with "tool" and "args"
- Use placeholder {{step_N_output}} (single braces) for previous outputs
- Keep it minimal — only the steps needed
- NEVER repeat the same tool twice unless explicitly needed

OUTPUT FORMAT:
{{
  "steps": [
    {{"tool": "get_latest_news", "args": {{"source": "ai"}}}},
    {{"tool": "write_file", "args": {{"path": "news.md", "content": "{{step_1_output}}"}}}}
  ]
}}

EXAMPLES:

User: "get latest AI news and save it as news.md"
{{"steps": [{{"tool": "get_latest_news", "args": {{"source": "ai"}}}}, {{"tool": "write_file", "args": {{"path": "news.md", "content": "{{step_1_output}}"}}}}]}}

User: "search for LangGraph news from last 5 days"
{{"steps": [{{"tool": "search_news", "args": {{"query": "LangGraph", "days_back": 5}}}}]}}

User: "list current directory"
{{"steps": [{{"tool": "list_directory", "args": {{"path": "."}}}}]}}

User: "get latest tech news"
{{"steps": [{{"tool": "get_latest_news", "args": {{"source": "tech"}}}}]}}
"""),
    ("user", "{input}")
])

_planner_chain = _PLANNER_PROMPT | _planner_llm | JsonOutputParser()


# ============================================================
# HARD RULES — fast pattern matching, no LLM needed
# FIX #5: 'ls' now checks word boundary, not substring
# FIX #6: news search hard rule added to prevent duplicate planning
# ============================================================

def _hard_rule_match(prompt: str) -> list | None:
    p     = prompt.lower().strip()
    words = p.split()

    # Directory listing — FIX #5: word boundary check
    if words and words[0] in ("ls", "dir"):
        return [{"tool": "list_directory", "args": {"path": "."}}]
    if any(x in p for x in ["list directory", "current directory", "show files"]):
        return [{"tool": "list_directory", "args": {"path": "."}}]

    # Read file
    m = re.search(r'read\s+(?:file\s+)?["\']?([^\s"\']+\.\w+)["\']?', p)
    if m:
        return [{"tool": "read_file", "args": {"path": m.group(1)}}]

    # Run command
    if words and words[0] in ("run", "execute"):
        cmd = prompt[len(words[0]):].strip()
        return [{"tool": "run_command", "args": {"command": cmd}}]

    # FIX #6: News keyword search — prevents planner from doubling up
    m = re.search(r'(?:search|find).*?news.*?(?:about|for|on)?\s+"?([a-zA-Z0-9 _-]+)"?', p)
    if m:
        query = m.group(1).strip()
        days  = 5
        dm    = re.search(r'last\s+(\d+)\s+days?', p)
        if dm:
            days = int(dm.group(1))
        steps = [{"tool": "search_news", "args": {"query": query, "days_back": days}}]
        # Check if save requested
        sm = re.search(r'save.*?(?:as|to)\s+([^\s]+\.(?:md|txt))', p)
        if sm:
            steps.append({"tool": "write_file", "args": {"path": sm.group(1), "content": "{step_1_output}"}})
        return steps

    # Simple news fetch
    for source in ["ai", "tech", "security", "hackernews", "agritech", "science", "business", "general"]:
        if source in p and "news" in p and "search" not in p:
            steps = [{"tool": "get_latest_news", "args": {"source": source}}]
            sm = re.search(r'save.*?(?:as|to)\s+([^\s]+\.(?:md|txt))', p)
            if sm:
                steps.append({"tool": "write_file", "args": {"path": sm.group(1), "content": "{step_1_output}"}})
            return steps

    return None


# ============================================================
# CORE: Execute one tool inside an active session
# ============================================================

async def _execute_tool(session: ClientSession, tool: str, args: dict) -> str:
    print(f"   🔧 {tool}({args})", flush=True)
    try:
        result = await session.call_tool(tool, args)
        return result.content[0].text if result.content else "⚠️ No output."
    except Exception as e:
        return f"❌ Tool error ({tool}): {e}"


# ============================================================
# MAIN AGENT — one session, sequential steps
# FIX #6: placeholder uses single braces {step_N_output}
# ============================================================

async def call_mcp_agent(prompt: str, history: list) -> str:
    print("🔌 [MCP BRIDGE] Planning...")

    steps = _hard_rule_match(prompt)

    if steps is None:
        try:
            plan  = _planner_chain.invoke({"input": prompt})
            steps = plan.get("steps", [])
            if not steps:
                raise ValueError("Empty plan")
        except Exception as e:
            print(f"   ⚠️ Planner failed: {e} → web_search fallback")
            steps = [{"tool": "web_search", "args": {"query": prompt}}]

    print(f"   📋 {len(steps)} step(s):")
    for i, s in enumerate(steps, 1):
        print(f"      Step {i}: {s['tool']}({s.get('args', {})})")

    step_outputs: dict[str, str] = {}
    final_output = ""

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("   ✅ MCP session ready")

            for i, step in enumerate(steps, 1):
                tool = step.get("tool", "web_search")
                args = step.get("args", {})

                # FIX #6: substitute {step_N_output} placeholders (single braces)
                resolved_args = {}
                for k, v in args.items():
                    if isinstance(v, str):
                        for placeholder, output in step_outputs.items():
                            v = v.replace("{" + placeholder + "}", output)
                    resolved_args[k] = v

                output = await _execute_tool(session, tool, resolved_args)
                step_outputs[f"step_{i}_output"] = output
                final_output = output

                print(f"   ✅ Step {i} done ({len(output)} chars)")

    return final_output


# ============================================================
# SYNC WRAPPER
# ============================================================

def run_tool_sync(tool_name: str, arguments: dict) -> str:
    async def _run():
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await _execute_tool(session, tool_name, arguments)
    return asyncio.run(_run())


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    async def test():
        tests = [
            "get latest AI news and save it as ai_news.md",
            "search for LangGraph news from last 5 days",
            "list current directory",
        ]
        for t in tests:
            print(f"\n{'='*50}\nPROMPT: {t}\n{'='*50}")
            result = await call_mcp_agent(t, [])
            print(f"RESULT (first 300 chars):\n{result[:300]}")

    asyncio.run(test())