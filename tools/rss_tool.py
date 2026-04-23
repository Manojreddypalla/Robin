# tools/rss_tool.py

import feedparser
import httpx
from datetime import datetime

# Trusted tech RSS feeds
TECH_RSS_FEEDS = {
    "HackerNews": "https://hnrss.org/frontpage",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
}


def fetch_rss_feed(feed_name: str, url: str, limit: int = 5):
    """
    Fetch and parse RSS feed safely.
    Returns structured articles.
    """

    try:
        response = httpx.get(url, timeout=10)
        feed = feedparser.parse(response.text)

        articles = []

        for entry in feed.entries[:limit]:
            articles.append({
                "source": feed_name,
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", "Unknown"),
                "summary": entry.get("summary", "")[:200]
            })

        return articles

    except Exception as e:
        return [{
            "source": feed_name,
            "error": str(e)
        }]


def tech_news_tool(query: str = None, limit_per_feed: int = 3):
    """
    Main Tool Function
    Can optionally filter by keyword query.
    """

    all_articles = []

    for name, url in TECH_RSS_FEEDS.items():
        articles = fetch_rss_feed(name, url, limit_per_feed)

        if query:
            articles = [
                article for article in articles
                if query.lower() in article.get("title", "").lower()
            ]

        all_articles.extend(articles)

    return all_articles
