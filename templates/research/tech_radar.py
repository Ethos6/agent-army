"""Tech Radar

A weekly radar of what developers are actually talking about. It reads the Hacker News front page
and trending discussions, clusters stories into themes, separates hype from substance, and rates
each theme Adopt / Trial / Assess / Hold for your stack.
"""
from army import Agent
from army.tools import fetch_url
from army.web import hacker_news, web_search

META = {
    "category": "research",
    "description": "Clusters what developers discuss on Hacker News into themes and rates each Adopt/Trial/Assess/Hold.",
    "example": "Tech radar for a Python backend team",
}
EVALS = [{"input": "Tech radar for a frontend team", "must_contain": ["Adopt", "Hold"], "max_seconds": 240}]


def build(llm=None, stories: str = "30"):
    return Agent(
        name="tech-radar",
        instructions=f"""You are a principal engineer curating a technology radar.

1. Call `hacker_news` with n={stories}. Open the 3-5 most relevant links with `fetch_url` to check substance.
2. Cluster stories into 4-7 themes relevant to the reader's stack. Use `web_search` to check maturity (releases, adoption).

Output a table: | Theme | Ring (Adopt/Trial/Assess/Hold) | Why | Evidence (links) |
Then ## Hype check (what is getting attention but lacks substance) and ## One thing to try this week.""",
        tools=[hacker_news, fetch_url, web_search],
        llm=llm,
        max_steps=12,
    )
