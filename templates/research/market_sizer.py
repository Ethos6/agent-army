"""Market Sizer

Estimates TAM, SAM and SOM two independent ways (top-down from published market data, bottom-up
from customer counts times price), shows every assumption and calculation, and reconciles the two
estimates. Investors and founders get a defensible number instead of a guess.
"""
from army import Agent
from army.tools import calculate, fetch_url
from army.web import web_search

META = {
    "category": "research",
    "description": "TAM/SAM/SOM estimated top-down and bottom-up with every assumption sourced and every sum calculated.",
    "example": "Market size for AI note-taking apps for doctors in the US",
}
EVALS = [{"input": "Market size for dog-walking apps in the UK", "must_contain": ["TAM", "SAM", "SOM", "Bottom-up"], "max_seconds": 300}]


def build(llm=None):
    return Agent(
        name="market-sizer",
        instructions="""You are a market-sizing analyst at a top consulting firm.

1. Top-down: find published market estimates with `web_search` / `fetch_url`; note source, year and definition.
2. Bottom-up: number of target customers x adoption rate x annual price. Source every input; label guesses as assumptions.
3. Compute everything with `calculate` and show the expressions.

Output:
## Definition of the market
## Top-down  (table: figure | value | source)
## Bottom-up  (table: input | value | source or ASSUMPTION)
## TAM / SAM / SOM  (both methods side by side)
## Reconciliation  (why they differ, which you trust more)
## Sensitivity  (which assumption moves the answer most)""",
        tools=[web_search, fetch_url, calculate],
        llm=llm,
        max_steps=14,
    )
