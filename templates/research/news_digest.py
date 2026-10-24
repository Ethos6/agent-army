"""News Digest

Reads the RSS/Atom feeds you trust (pass them with --opt feeds=url1,url2 or in the task), removes
duplicates across sources, ranks stories by importance to your stated interests, and writes a
five-minute digest with links. Schedule it with `army schedule` for a daily briefing.
"""
from army import Agent
from army.tools import fetch_url
from army.web import read_feed

META = {
    "category": "research",
    "description": "Reads your trusted RSS feeds, de-duplicates, ranks by your interests, and writes a 5-minute digest.",
    "example": "Digest of https://hnrss.org/frontpage and https://feeds.bbci.co.uk/news/technology/rss.xml for an AI startup founder",
}
EVALS = [{"input": "Digest https://hnrss.org/frontpage for a developer", "must_contain": ["Top stories", "http"], "max_seconds": 180}]


def build(llm=None, feeds: str = ""):
    feed_line = f"Default feeds: {feeds}." if feeds else "Use the feed URLs given in the request."
    return Agent(
        name="news-digest",
        instructions=f"""You are a news editor. {feed_line}

1. Call `read_feed` for each feed. Fetch an article with `fetch_url` only when the summary is too thin to judge it.
2. Merge stories that cover the same event. Rank by relevance to the reader's stated interests, then by impact.

Output:
## Top stories (5)  - headline, 2-sentence why-it-matters, link
## Quick hits (up to 8)  - one line + link
## Worth watching  - developing stories
Keep it readable in five minutes.""",
        tools=[read_feed, fetch_url],
        llm=llm,
    )
