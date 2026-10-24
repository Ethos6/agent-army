"""Decision Helper

Helps you choose between options without fooling yourself. It surfaces the criteria that actually
matter to you, weights them, scores every option with the arithmetic shown, runs a sensitivity
check ("would the winner change if X mattered more?"), and names the cheapest way to reduce
uncertainty before committing.
"""
from army import Agent
from army.tools import calculate
from army.web import web_search

META = {
    "category": "starter",
    "description": "Weighted decision matrix with exact scores, a sensitivity check and the cheapest next test.",
    "example": "Should we build our analytics in-house, buy a SaaS tool, or use an open-source stack? Team of 4, budget tight",
}
EVALS = [{"input": "Choose between learning Python or JavaScript first for data jobs", "must_contain": ["Weight", "Sensitivity"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="decision-helper",
        instructions="""You are a decision analyst.

1. List the options and 4-7 criteria implied by the user's goals and constraints. Assign weights summing to 100.
2. Score each option 1-10 per criterion with a one-line reason (use `web_search` for facts you don't know).
3. Compute weighted totals with `calculate`, showing the expression.
4. Sensitivity: re-weight the top two criteria by +/-15 and recompute. Does the winner change?

Output: decision matrix table (Criterion | Weight | Option scores...), totals, ## Sensitivity, ## Recommendation,
## Cheapest test before committing (something doable in a week).""",
        tools=[calculate, web_search],
        llm=llm,
    )
