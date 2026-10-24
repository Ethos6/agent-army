"""Meeting Prep

Before a meeting with a company or person, it researches the organisation's recent news, priorities
and context, then gives you a one-page brief: who they are, what they likely care about, talking
points, questions to ask, and landmines to avoid.
"""
from army import Agent
from army.tools import fetch_url
from army.web import crawl_site, web_search

META = {
    "category": "business",
    "description": "One-page brief before any meeting: their priorities, recent news, talking points and landmines.",
    "example": "Sales meeting with the head of operations at a mid-size logistics company; we sell route-optimization software",
}
EVALS = [{"input": "Partnership meeting with the Python Software Foundation", "must_contain": ["Talking points", "Questions to ask"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="meeting-prep",
        instructions="""You are a chief of staff preparing a busy executive.

Research the organisation with `web_search` (news from the last 90 days, strategy, leadership, earnings or funding)
and its website with `crawl_site` or `fetch_url`.

Output (fits on one page):
## Who they are (3 lines)
## What's happening now (3-5 recent developments with dates and links)
## What they likely care about in this meeting
## Talking points (tie our offer to their priorities)
## Questions to ask (5)
## Landmines (topics or claims to avoid, and why)
## Desired outcome and next step""",
        tools=[web_search, fetch_url, crawl_site],
        llm=llm,
        max_steps=12,
    )
