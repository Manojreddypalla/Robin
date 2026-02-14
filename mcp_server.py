# mcp_server.py

import sys
import os
import subprocess
import requests
import threading
import time
from pathlib import Path
from dotenv import load_dotenv


# ---------------- IMPORT MCP ----------------

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("FATAL: mcp[cli] not installed.", file=sys.stderr)
    sys.exit(1)


# ---------------- CONFIG ----------------

load_dotenv()
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")


# ---------------- INIT SERVER ----------------

mcp = FastMCP("Robin-Ultimate-Agent")


# ---------------- TOOLS ----------------

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files in a directory."""
    try:
        p = Path(path).resolve()

        if not p.exists():
            return "Path does not exist"

        items = os.listdir(p)

        return "\n".join(items) if items else "(Empty folder)"

    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file."""
    try:
        return Path(path).read_text(
            encoding="utf-8",
            errors="ignore"
        )

    except Exception as e:
        return f"Read error: {e}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write to a file."""
    try:
        p = Path(path).resolve()

        p.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        p.write_text(
            content,
            encoding="utf-8"
        )

        return f"Written: {p}"

    except Exception as e:
        return f"Write error: {e}"


@mcp.tool()
def web_search(query: str) -> str:
    """Search the internet using Brave API."""
    if not BRAVE_API_KEY:
        return "Error: BRAVE_API_KEY missing."

    try:
        print(f"🌍 SEARCH: {query}", file=sys.stderr)

        url = "https://api.search.brave.com/res/v1/web/search"

        headers = {
            "X-Subscription-Token": BRAVE_API_KEY
        }

        params = {
            "q": query,
            "count": 5
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:

            results = response.json().get("web", {}).get("results", [])

            if not results:
                return "No results found."

            return "\n\n".join([
                f"Title: {r['title']}\n"
                f"Snippet: {r.get('description', '')}\n"
                f"Link: {r.get('url')}"
                for r in results
            ])

        return f"Error: {response.status_code}"

    except Exception as e:
        return f"Connection failed: {e}"


@mcp.tool()
def get_latest_news(source: str = "general") -> str:
    """Fetch news from RSS."""

    import feedparser

    PRESETS = {
        "general": "http://feeds.bbci.co.uk/news/rss.xml",
        "tech": "https://techcrunch.com/feed/"
    }

    url = PRESETS.get(source.lower(), source)

    try:
        feed = feedparser.parse(url)

        if not feed.entries:
            return "No entries found."

        summary = f"📰 News ({source}):\n"

        for entry in feed.entries[:5]:
            summary += f"\n• {entry.title}\n  🔗 {entry.link}\n"

        return summary

    except Exception as e:
        return f"Feed Error: {e}"


@mcp.tool()
def speak(text: str) -> str:
    """Speak text using TTS."""

    import pyttsx3

    try:
        engine = pyttsx3.init()

        engine.say(text)
        engine.runAndWait()

        return "✅ Spoken."

    except Exception as e:
        return f"Speech Error: {e}"


# ---------------- RUN ----------------

if __name__ == "__main__":

    # Keep logs on stderr (important for MCP stdio)
    print("🚀 Server Starting...", file=sys.stderr)

    mcp.run(transport="stdio")