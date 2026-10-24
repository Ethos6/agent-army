"""Due Diligence Team

An investment-committee workflow for a startup: a market analyst, a product and technology analyst
and a risk analyst research the company in turn, each building on the earlier sections, then a partner writes the investment
memo with a clear recommendation and the questions to ask the founders.
"""
from army import Agent, Pipeline
from army.tools import calculate, fetch_url
from army.web import crawl_site, web_search

META = {
    "category": "business",
    "description": "Market, product and risk analysts research a startup; a partner writes the investment memo.",
    "example": "Due diligence on https://www.example-startup.com (seed round, AI for logistics)",
}
EVALS = [{"input": "Due diligence on the company behind https://www.python.org as if it were a startup", "must_contain": ["Recommendation", "Questions for the founders"], "max_seconds": 600}]


def build(llm=None):
    tools = [web_search, fetch_url, crawl_site, calculate]
    market = Agent("market-analyst", """Research the company's market: size, growth, competitors, timing. Read the company site
with `crawl_site`, search for competitors and market data. Output an evidence-backed market section with sources.""", tools, llm=llm)
    product = Agent("product-analyst", """Assess the product and technology: what it does, differentiation, defensibility, team signals,
traction signals (customers, hiring, releases). Add to the previous analysis; cite sources.""", tools, llm=llm)
    risk = Agent("risk-analyst", """List the top risks (market, execution, technical, regulatory, competition, financing), each with likelihood,
impact and what evidence would retire it. Keep the earlier sections intact and append yours.""", tools, llm=llm)
    partner = Agent("partner", """Write the investment memo from the analysis ONLY:
# Investment memo: <company>
## Summary and recommendation (Invest / Pass / Track, with the single biggest reason)
## Market  ## Product and moat  ## Traction  ## Risks (table)  ## Valuation sanity check (if data exists)
## Questions for the founders (8 sharp questions)""", llm=llm)
    return Pipeline(market, product, risk, partner, name="due-diligence-team")
