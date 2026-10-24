"""Investment Comparison

Compares two to five tickers side by side: price performance over several periods from public market
data, recent news, business quality signals and key risks, presented as a comparison table and a
balanced discussion. Research support only, not investment advice.
"""
from army import Agent
from army.tools import calculate
from army.web import stock_history, web_search

META = {
    "category": "business",
    "description": "Side-by-side performance, news and risks for 2-5 tickers, every number from tools.",
    "example": "Compare NVDA, AMD and INTC",
}
EVALS = [{"input": "Compare KO and PEP", "must_contain": ["KO", "PEP", "not investment advice"], "max_seconds": 300}]


def build(llm=None):
    return Agent(
        name="investment-compare",
        instructions="""You are an investment research analyst.

For each ticker: `stock_history` for "1y" and "3mo"; `web_search` for recent news and the business model.
Use `calculate` for any comparison.

Output:
| Ticker | Last | 3-month | 1-year | 1y high / low | Notes |
## Business quality (moat, growth, margins as reported in sources)
## Recent news (per ticker, with links)
## Key risks
## How they differ for an investor (growth vs income vs stability)
_Not investment advice._""",
        tools=[stock_history, web_search, calculate],
        llm=llm,
        max_steps=16,
    )
