"""Finance Research Team

A manager agent delegates to two specialists: a market-data analyst that pulls price history and
computes returns, and a news analyst that gathers recent developments. The manager decides what to
ask each one, merges their work, and writes the final note. A small example of hierarchical,
manager-and-workers orchestration.
"""
from army import Agent
from army.tools import calculate
from army.web import stock_history, web_search

META = {
    "category": "teams",
    "description": "A manager delegates to market-data and news analysts, then writes one research note.",
    "example": "How have the big three cloud providers' stocks done this year and why?",
}
EVALS = [{"input": "How has Apple stock done over 6 months and why?", "must_contain": ["AAPL", "not investment advice"], "max_seconds": 400}]


def build(llm=None):
    data = Agent("market-data-analyst", """Fetch price history with `stock_history` for every ticker asked about and compute
returns/differences with `calculate`. Return a compact table of numbers only.""", tools=[stock_history, calculate], llm=llm)
    news = Agent("news-analyst", """Use `web_search` to find the 3-5 most important recent developments for the companies asked about.
Return bullets with dates and source URLs.""", tools=[web_search], llm=llm)
    return Agent(
        "finance-manager",
        """You manage a research team. Map company names to tickers yourself. Delegate: ask the market-data analyst for numbers
and the news analyst for drivers (you may call each more than once). Then write:
## Summary  ## Performance (table from the data analyst)  ## What drove it (from the news analyst, with links)
## Risks to watch
_Not investment advice._""",
        tools=[data.as_tool("Get price history and computed returns for tickers."),
               news.as_tool("Get recent dated news with sources for companies.")],
        llm=llm,
        max_steps=10,
    )
