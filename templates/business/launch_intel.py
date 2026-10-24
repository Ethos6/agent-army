"""Product Launch Intel

Analyses a competitor's product launch (announcement page, docs, press coverage, community
reaction) and tells you what launched, who it targets, how the market reacted, and what it means
for you: threats, opportunities and a recommended response.
"""
from army import Agent
from army.tools import fetch_url
from army.web import hacker_news, web_search

META = {
    "category": "business",
    "description": "What a competitor launched, how the market reacted, and the response you should make.",
    "example": "Analyse the latest launch from a major note-taking app competitor",
}
EVALS = [{"input": "Analyse the most recent Python release launch", "must_contain": ["What launched", "Recommended response"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="launch-intel",
        instructions="""You are a go-to-market intelligence analyst.

1. Find the launch with `web_search` and read the announcement and docs with `fetch_url`.
2. Gauge reaction: press coverage, reviews, and developer discussion (`hacker_news` if technical).

Output:
## What launched  (features, pricing, availability, dates)
## Who it's for and the positioning
## Market reaction  (positive / negative signals with links)
## Implications for us  (threats, opportunities)
## Recommended response  (now / this quarter / ignore - with reasoning)""",
        tools=[web_search, fetch_url, hacker_news],
        llm=llm,
        max_steps=12,
    )
