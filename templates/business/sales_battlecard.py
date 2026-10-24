"""Sales Battlecard

Builds a competitive battlecard a sales rep can use mid-call: how the competitor positions itself,
where we win and lose, landmine questions to plant, objection handling with proof points, and a
pricing comparison taken from their public pages.
"""
from army import Agent
from army.tools import calculate, fetch_url
from army.web import web_search

META = {
    "category": "business",
    "description": "A mid-call battlecard: their pitch, where we win, objection handling and landmine questions.",
    "example": "Battlecard for our product https://ourco.com against https://competitor.com",
}
EVALS = [{"input": "Battlecard: PostgreSQL versus MySQL for a database vendor's sales team", "must_contain": ["Objection", "Landmine"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="sales-battlecard",
        instructions="""You are a product-marketing manager writing a battlecard. Read both companies' sites and pricing with
`fetch_url`; search for reviews, comparisons and complaints with `web_search`.

Output:
# <Us> vs <Them>
**Their pitch in one line:** (their words)
## Where we win (3) / Where they win (3)  - be honest
## Landmine questions to ask the prospect (4)
## Objection handling  (| Objection | Response | Proof point + source |)
## Pricing comparison  (exact public figures only; use `calculate`)
## Customers who switched  (only if found with a source)""",
        tools=[fetch_url, web_search, calculate],
        llm=llm,
        max_steps=12,
    )
