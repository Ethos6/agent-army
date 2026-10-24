"""Competitor Watch

Give it your URL and your competitors' URLs. It reads every page and writes a snapshot table
(positioning in their own words, target customer, exact pricing, recent changes), then where you
win, where you are exposed, and three moves for this quarter, each tied to evidence. It only
reports pricing it actually saw.
"""
from army import Agent
from army.tools import calculate, fetch_url

META = {
    "category": "business",
    "description": "Turns competitor homepages and pricing pages into a positioning table, gaps, and three concrete moves.",
    "example": "We are https://ourco.com, compare us with https://rival1.com/pricing and https://rival2.com",
}
EVALS = [{"input": "Compare https://www.python.org with https://www.rust-lang.org as competing products", "must_contain": ["Snapshot", "Where we win", "3 moves"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="competitor-watch",
        instructions="""You are a competitive-intelligence analyst. Fetch every URL the user gives.

Output (Markdown):
## Snapshot
| Company | Positioning (their words) | Target customer | Pricing (exact figures) | Notable recent change |
## Where we win
## Where we are exposed
## 3 moves for this quarter
Each move: what to do, why now, and the signal from the pages that justifies it (quote under 15 words).

Rules: only report pricing you actually saw; write "not published" otherwise. Use `calculate` for price comparisons.""",
        tools=[fetch_url, calculate],
        llm=llm,
        max_steps=12,
    )
