# mcp_server.py

import sys
import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

mcp = FastMCP("Robin-MCP-Server")

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ============================================================
# HELPERS
# ============================================================

def summarize_text(text: str, max_sentences: int = 4) -> str:
    if not text:
        return "No content available."
    sentences = re.split(r'(?<=[.!?]) +', text)
    return " ".join(sentences[:max_sentences]) if len(sentences) > max_sentences else text[:500]


def extract_article_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        if article.text and len(article.text) > 200:
            return article.text
    except Exception:
        pass
    try:
        from bs4 import BeautifulSoup
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")
        return "\n".join(p.get_text() for p in soup.find_all("p"))
    except Exception:
        return ""


# ============================================================
# FILE SYSTEM TOOLS
# ============================================================

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files and folders at the given path."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"❌ Path does not exist: {path}"
        items = os.listdir(p)
        return "\n".join(f"• {item}" for item in items) if items else f"📂 Empty: {path}"
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read and return the content of a file."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"❌ File not found: {path}"
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"✅ Written: {p}"
    except Exception as e:
        return f"❌ Error: {e}"


# ============================================================
# WEB SEARCH
# ============================================================

@mcp.tool()
def web_search(query: str) -> str:
    """Search the internet and return summarized results."""
    import time

    print(f"🌍 Searching: {query}", file=sys.stderr)

    try:
        from ddgs import DDGS
    except ImportError:
        return "❌ ddgs not installed. Run: pip install ddgs"

    results = []
    for attempt in range(3):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if results:
                break
        except Exception as e:
            print(f"⚠️ DDG attempt {attempt+1}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))

    # Fallback: news search
    if not results:
        try:
            with DDGS() as ddgs:
                results = [
                    {"title": r.get("title",""), "body": r.get("body",""), "href": r.get("url","")}
                    for r in ddgs.news(query, max_results=5)
                ]
        except Exception:
            pass

    if not results:
        return f"❌ No results for: {query}"

    context_parts = []
    sources = []
    for r in results:
        body = r.get("body", "") or r.get("snippet", "")
        link = r.get("href", "") or r.get("url", "")
        if body:
            context_parts.append(body)
        if link:
            sources.append(link)

    output = "\n\n".join(context_parts)
    if sources:
        output += "\n\nSources:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(sources, 1))

    return output


# ============================================================
# NEWS — NewsAPI primary + RSS fallback
# ============================================================

NEWSAPI_CATEGORIES = {
    "general":    {"category": "general"},
    "tech":       {"category": "technology"},
    "science":    {"category": "science"},
    "business":   {"category": "business"},
    "health":     {"category": "health"},
    "sports":     {"category": "sports"},
    "ai":         {"q": "artificial intelligence OR LLM OR machine learning", "sortBy": "publishedAt"},
    "security":   {"q": "cybersecurity OR hacking OR vulnerability", "sortBy": "publishedAt"},
    "hackernews": {"q": "startup OR programming OR open source", "sortBy": "popularity"},
    "agritech":   {"q": "agritech OR precision farming OR agricultural AI", "sortBy": "publishedAt"},
}

RSS_FALLBACK = {
    "general":    "http://feeds.bbci.co.uk/news/rss.xml",
    "tech":       "https://techcrunch.com/feed/",
    "ai":         "https://www.marktechpost.com/feed/",
    "hackernews": "https://hnrss.org/frontpage",
    "security":   "https://feeds.feedburner.com/TheHackersNews",
    "agritech":   "https://agfundernews.com/feed",
}


def _newsapi_fetch(source: str) -> str:
    params = NEWSAPI_CATEGORIES[source].copy()
    params["apiKey"]   = NEWS_API_KEY
    params["pageSize"] = 5
    params["language"] = "en"

    if "q" in params:
        url = "https://newsapi.org/v2/everything"
    else:
        url = "https://newsapi.org/v2/top-headlines"
        params["country"] = "us"

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise ValueError(f"NewsAPI: {data.get('message')}")

    articles = data.get("articles", [])
    if not articles:
        raise ValueError("No articles")

    output = f"📡 NewsAPI — {source.upper()}\n\n"
    for a in articles:
        title  = a.get("title", "No title")
        desc   = (a.get("description") or "")[:200]
        link   = a.get("url", "")
        src    = a.get("source", {}).get("name", "")
        date   = (a.get("publishedAt") or "")[:10]
        output += f"📰 {title}\n   {desc}\n   🗞️ {src} · {date}\n   🔗 {link}\n\n"

    return output


def _rss_fallback(source: str) -> str:
    import feedparser
    url  = RSS_FALLBACK.get(source, RSS_FALLBACK.get("tech", ""))
    if not url:
        return f"❌ No RSS feed for: {source}"
    feed = feedparser.parse(url)
    if not feed.entries:
        return "❌ RSS returned no results."
    output = f"📡 RSS — {source.upper()}\n\n"
    for entry in feed.entries[:5]:
        title   = entry.get("title", "No title")
        link    = entry.get("link", "")
        summary = (entry.get("summary") or "")[:200]
        output += f"📰 {title}\n   {summary}\n   🔗 {link}\n\n"
    return output


@mcp.tool()
def get_latest_news(source: str = "ai") -> str:
    """
    Get latest news headlines.
    source: general | tech | ai | science | business | health | sports | security | hackernews | agritech
    """
    source = source.lower().strip()
    if source not in NEWSAPI_CATEGORIES:
        return f"❌ Unknown source '{source}'. Options: {', '.join(NEWSAPI_CATEGORIES.keys())}"

    print(f"📰 [NEWS] {source}", file=sys.stderr)

    if NEWS_API_KEY:
        try:
            result = _newsapi_fetch(source)
            print("   ✅ NewsAPI OK", file=sys.stderr)
            return result
        except Exception as e:
            print(f"   ⚠️ NewsAPI failed: {e} → RSS fallback", file=sys.stderr)

    if source in RSS_FALLBACK:
        try:
            return _rss_fallback(source)
        except Exception as e:
            return f"❌ Both NewsAPI and RSS failed: {e}"

    return f"❌ No fallback for '{source}' and NEWS_API_KEY is not set."


@mcp.tool()
def search_news(query: str, days_back: int = 3) -> str:
    """
    Search news articles by keyword using NewsAPI /v2/everything.
    query     : keyword or phrase
    days_back : how many days back to search (default 3)
    """
    if not NEWS_API_KEY:
        return "❌ NEWS_API_KEY not set in .env"

    from datetime import datetime, timedelta
    date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print(f"🔍 [NEWS SEARCH] '{query}' last {days_back}d", file=sys.stderr)

    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        query,
                "from":     date_from,
                "sortBy":   "publishedAt",
                "language": "en",
                "pageSize": 5,
                "apiKey":   NEWS_API_KEY,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            return f"❌ NewsAPI: {data.get('message')}"

        articles = data.get("articles", [])
        if not articles:
            return f"❌ No articles found for: {query}"

        output = f"🔍 News: '{query}' (last {days_back} days)\n\n"
        for a in articles:
            title = a.get("title", "No title")
            desc  = (a.get("description") or "")[:200]
            link  = a.get("url", "")
            src   = a.get("source", {}).get("name", "")
            date  = (a.get("publishedAt") or "")[:10]
            output += f"📰 {title}\n   {desc}\n   🗞️ {src} · {date}\n   🔗 {link}\n\n"

        return output

    except Exception as e:
        return f"❌ Search error: {e}"


# ============================================================
# TEXT TO SPEECH
# ============================================================

@mcp.tool()
def speak(text: str) -> str:
    """Speak text aloud using local TTS."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text[:500])  # cap at 500 chars to avoid forever speech
        engine.runAndWait()
        return "✅ Spoken"
    except Exception as e:
        return f"❌ TTS error: {e}"


# ============================================================
# RUN COMMAND
# ============================================================

@mcp.tool()
def run_command(command: str) -> str:
    """Execute a shell command and return output."""
    try:
        import subprocess
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=20
        )
        output = result.stdout.strip()
        error  = result.stderr.strip()
        if output and error:
            return f"⚠️ stdout:\n{output}\n\nstderr:\n{error}"
        return f"✅ {output}" if output else (f"❌ {error}" if error else "✅ Done (no output)")
    except Exception as e:
        return f"❌ Command failed: {e}"


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    print("🚀 Robin MCP Server starting...", file=sys.stderr)
    mcp.run(transport="stdio")