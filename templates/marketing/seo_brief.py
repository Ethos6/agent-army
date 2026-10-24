"""SEO Content Brief

Builds a brief a writer can rank with. It analyses the search intent behind a keyword, reads the
pages that currently rank, finds the subtopics and questions they cover (and what they miss), and
outputs an outline, title and meta options, internal-link ideas and an information-gain angle.
"""
from army import Agent
from army.tools import fetch_url, text_stats
from army.web import web_search

META = {
    "category": "marketing",
    "description": "Search intent, what ranking pages cover and miss, an outline, titles, metas and a unique angle.",
    "example": "SEO brief for 'best project management software for small teams'",
}
EVALS = [{"input": "SEO brief for 'how to brew cold brew coffee'", "must_contain": ["Search intent", "Outline", "Meta"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="seo-brief",
        instructions="""You are an SEO content strategist.

1. `web_search` the keyword. Open the top 4-5 organic results with `fetch_url`; measure them with `text_stats`.
2. Determine search intent (informational / commercial / transactional / navigational).

Output:
## Search intent
## What ranking pages cover  (table: URL | angle | length | notable sections)
## Content gaps  (what none of them cover well = our information gain)
## Outline  (H1, H2s, H3s, with notes)
## Title options (3, under 60 chars) and Meta descriptions (2, under 155 chars)
## Questions to answer  (People-also-ask style)
## Target length and internal link ideas""",
        tools=[web_search, fetch_url, text_stats],
        llm=llm,
        max_steps=12,
    )
