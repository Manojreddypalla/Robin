import os
import subprocess
import sys
import datetime
import psutil
import pyperclip
import pyttsx3
import requests
import threading  # <--- Required for background alarms
import time       # <--- Required for waiting
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# ---------------- CONFIG ----------------

load_dotenv()
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
SANDBOX_DIR = None 

mcp = FastMCP("Robin-Ultimate-Agent")

# ---------------- SECURITY ----------------

def validate_path(path: str) -> Path:
    target = Path(path).resolve()
    if SANDBOX_DIR:
        base = Path(SANDBOX_DIR).resolve()
        if not str(target).startswith(str(base)):
            raise PermissionError("Access denied")
    return target

# ---------------- EXISTING TOOLS ----------------

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files in a directory."""
    try:
        p = validate_path(path)
        if not p.exists(): return "Path does not exist"
        items = os.listdir(p)
        return "\n".join(items) if items else "(Empty folder)"
    except Exception as e: return f"Error: {e}"

@mcp.tool()
def read_file(path: str) -> str:
    """Read a file."""
    try:
        return validate_path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e: return f"Read error: {e}"

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write to a file."""
    try:
        p = validate_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written: {p}"
    except Exception as e: return f"Write error: {e}"

@mcp.tool()
def run_powershell(command: str) -> str:
    """Run a PowerShell command."""
    forbidden = ["rm -r", "Remove-Item -Recurse", "format c:"]
    if any(bad in command.lower() for bad in forbidden):
        return "Blocked dangerous command"
    try:
        print(f"EXEC: {command}", file=sys.stderr)
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except Exception as e: return f"Exec error: {e}"

@mcp.tool()
def web_search(query: str) -> str:
    """Search the internet using Brave API."""
    if not BRAVE_API_KEY: return "Error: BRAVE_API_KEY missing."
    try:
        print(f"🌍 SEARCH: {query}", file=sys.stderr)
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": BRAVE_API_KEY}
        params = {"q": query, "count": 5}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            results = response.json().get("web", {}).get("results", [])
            if not results: return "No results found."
            return "\n\n".join([f"Title: {r['title']}\nSnippet: {r.get('description','')}" for r in results])
        return f"Error: {response.status_code}"
    except Exception as e: return f"Connection failed: {e}"


# ---------------- RUN ----------------

if __name__ == "__main__":
    print("🚀 Robin Ultimate Server (with Alarms) Running", file=sys.stderr)
    mcp.run()