# mcp_server.py

import sys
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

# MCP
from mcp.server.fastmcp import FastMCP

# load env if needed later
load_dotenv()

# ---------------- INIT SERVER ----------------

mcp = FastMCP("Robin-Ultimate-Agent")


# ---------------- FILE SYSTEM TOOLS ----------------

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files in a directory."""
    try:
        p = Path(path).resolve()

        if not p.exists():
            return "❌ Path does not exist"

        items = os.listdir(p)

        return "\n".join(items) if items else "(Empty folder)"

    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read file content."""
    try:
        return Path(path).read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception as e:
        return f"❌ Read error: {e}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to file."""
    try:
        p = Path(path).resolve()

        p.parent.mkdir(parents=True, exist_ok=True)

        p.write_text(content, encoding="utf-8")

        return f"✅ Written: {p}"

    except Exception as e:
        return f"❌ Write error: {e}"


# ---------------- DUCKDUCKGO SEARCH ----------------

@mcp.tool()
def web_search(query: str) -> str:
    """
    Search internet using DuckDuckGo (no API key required).
    """

    try:

        print(f"🌍 DuckDuckGo search: {query}", file=sys.stderr)

        url = "https://duckduckgo.com/html/"

        params = {
            "q": query
        }

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return "❌ Search failed"

        # simple parsing
        text = response.text

        results = []

        for line in text.split("\n"):

            if 'result__a' in line:

                try:
                    title = line.split(">")[1].split("<")[0]
                    results.append(title)
                except:
                    pass

            if len(results) >= 5:
                break

        if not results:
            return "No results found."

        return "\n".join([f"• {r}" for r in results])

    except Exception as e:
        return f"❌ Search error: {e}"


# ---------------- NEWS TOOL ----------------

@mcp.tool()
def get_latest_news(source: str = "general") -> str:
    """
    Get latest news from RSS feeds.
    Supports: general, tech, ai, hackernews
    """

    import feedparser

    PRESETS = {

        "general": "http://feeds.bbci.co.uk/news/rss.xml",

        "tech": "https://techcrunch.com/feed/",

        "ai": "https://feeds.feedburner.com/artificialintelligence-news",

        "hackernews": "https://hnrss.org/frontpage",

        "security": "https://feeds.feedburner.com/TheHackersNews"
    }

    source = source.lower()

    url = PRESETS.get(source, source)

    try:

        print(f"📰 Fetching news: {source}", file=sys.stderr)

        feed = feedparser.parse(url)

        if not feed.entries:
            return "❌ No news found."

        summary = f"📰 Latest News ({source}):\n\n"

        for entry in feed.entries[:5]:

            summary += (
                f"• {entry.title}\n"
                f"  🔗 {entry.link}\n\n"
            )

        return summary

    except Exception as e:
        return f"❌ News error: {e}"


# ---------------- TTS TOOL ----------------

@mcp.tool()
def speak(text: str) -> str:
    """Speak text using local TTS."""

    try:

        import pyttsx3

        engine = pyttsx3.init()

        engine.say(text)

        engine.runAndWait()

        return "✅ Spoken"

    except Exception as e:
        return f"❌ Speech error: {e}"


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":

    print("🚀 Robin MCP Server starting...", file=sys.stderr)

    mcp.run(transport="stdio")
