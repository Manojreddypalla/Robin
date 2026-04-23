import os
import subprocess
import sys
import datetime
import psutil       # pip install psutil
import pyperclip    # pip install pyperclip
import pyttsx3      # pip install pyttsx3
import requests     # pip install requests
import feedparser   # pip install feedparser
import threading
import time
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

# ---------------- 📂 FILE & SYSTEM TOOLS ----------------

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
def open_in_notepad(path: str) -> str:
    """Open a file in Notepad (Windows only)."""
    try:
        p = validate_path(path)
        subprocess.Popen(["notepad.exe", str(p)], creationflags=subprocess.CREATE_NO_WINDOW)
        return "Notepad opened"
    except Exception as e: return f"Error: {e}"

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

# ---------------- 🌍 WEB & SEARCH TOOLS ----------------

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
            return "\n\n".join([f"Title: {r['title']}\nSnippet: {r.get('description','')}\nLink: {r.get('url')}" for r in results])
        return f"Error: {response.status_code}"
    except Exception as e: return f"Connection failed: {e}"

@mcp.tool()
def get_weather(city: str) -> str:
    """Get weather using wttr.in (No API key needed)."""
    try:
        url = f"https://wttr.in/{city.lower()}?format=%C+%t"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f"Weather in {city}: {response.text.strip()}"
        return "Error fetching weather."
    except Exception as e: return f"Connection Error: {e}"

@mcp.tool()
def get_latest_news(source: str = "general") -> str:
    """
    Fetch news from RSS. 
    Args: source (category like 'tech' OR a direct URL).
    """
    PRESETS = {
        "general": "http://feeds.bbci.co.uk/news/rss.xml",
        "tech": "https://techcrunch.com/feed/",
        "science": "https://www.sciencedaily.com/rss/top/science.xml",
        "finance": "https://feeds.bloomberg.com/markets/news.rss",
        "sports": "https://www.espn.com/espn/rss/news",
        "gaming": "https://www.gamespot.com/feeds/news/"
    }
    
    url = source if source.startswith("http") else PRESETS.get(source.lower())
    if not url: return f"Unknown category. Try: {', '.join(PRESETS.keys())}"

    try:
        feed = feedparser.parse(url)
        if not feed.entries: return "No entries found."
        summary = f"📰 News ({source}):\n"
        for entry in feed.entries[:5]:
            summary += f"\n• {entry.title}\n  🔗 {entry.link}\n"
        return summary
    except Exception as e: return f"Feed Error: {e}"


# ---------------- RUN ----------------

if __name__ == "__main__":
    print("🚀 Robin Ultimate Server Running", file=sys.stderr)
    mcp.run()