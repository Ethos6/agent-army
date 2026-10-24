"""Stock Snapshot

One-page snapshot of a listed company: price trend from public market data, recent news found by
web search, and the bull and bear case. Every number comes from a tool. This is research support,
not investment advice, and the agent says so.
"""
from army import Agent
from army.tools import calculate
from army.web import stock_history, web_search

META = {
    "category": "starter",
    "description": "Price trend, recent news and the bull/bear case for a ticker, with every number sourced from tools.",
    "example": "Give me a snapshot of MSFT",
}
EVALS = [{"input": "Snapshot of AAPL", "must_contain": ["AAPL", "not investment advice"], "max_seconds": 180}]


def build(llm=None, period: str = "1y"):
    return Agent(
        name="stock-snapshot",
        instructions=f"""You are an equity research assistant.

1. Call `stock_history` with period "{period}" (and "1mo" for the short-term move).
2. Use `web_search` for news from the last 30 days about the company (earnings, guidance, product, regulation).
3. Compute any extra percentages with `calculate`.

Output:
## <TICKER> snapshot
| Metric | Value |  (last price, change over period, high, low, 1-month change)
## What moved it  (3 bullets, each with a source URL)
## Bull case / Bear case  (2-3 bullets each)
## What to watch next  (dated events if known)
_This is not investment advice._""",
        tools=[stock_history, web_search, calculate],
        llm=llm,
    )
