"""Strategy Consultant

Works a business problem the way a top-tier consultant would: frames the real question, builds an
issue tree, gathers market evidence with live web research, sizes the options with numbers, and
ends with a recommendation, risks and a 30-60-90 day plan.
"""
from army import Agent
from army.tools import calculate, fetch_url
from army.web import web_search

META = {
    "category": "business",
    "description": "Issue tree, live market evidence, quantified options and a 30-60-90 plan for any business problem.",
    "example": "Our B2B SaaS churn rose from 3% to 5% monthly. What should we do?",
}
EVALS = [{"input": "Should a regional coffee chain launch a subscription?", "must_contain": ["Recommendation", "90"], "max_seconds": 300}]


def build(llm=None):
    return Agent(
        name="strategy-consultant",
        instructions="""You are a senior strategy consultant. Hypothesis-driven, numbers-first, no fluff.

1. Restate the core question in one sentence and list what would have to be true for each answer.
2. Build an issue tree (MECE) of 3-4 branches.
3. Gather evidence with `web_search` / `fetch_url` (benchmarks, competitor moves, market data). Cite sources.
4. Quantify 2-3 options with `calculate` (impact, cost, payback). Label assumptions.

Output: ## The question, ## Issue tree, ## What the evidence says, ## Options compared (table),
## Recommendation, ## Risks and mitigations, ## 30-60-90 day plan.""",
        tools=[web_search, fetch_url, calculate],
        llm=llm,
        max_steps=14,
    )
