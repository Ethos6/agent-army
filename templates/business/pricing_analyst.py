"""Pricing Analyst

Designs or reviews pricing. It collects competitor price points, maps your value metric, models
revenue for candidate tiers with exact arithmetic, and recommends a structure with good-better-best
packaging, anchor prices and the experiment to validate it.
"""
from army import Agent
from army.tools import calculate, fetch_url
from army.web import web_search

META = {
    "category": "business",
    "description": "Competitor price points, value-metric choice, modelled tiers and a validation experiment.",
    "example": "Price our team task-management SaaS; competitors charge 8-15 USD per seat",
}
EVALS = [{"input": "Price a mobile habit-tracking app", "must_contain": ["Tier", "Experiment"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="pricing-analyst",
        instructions="""You are a pricing strategist.

1. Collect competitor pricing (`web_search`, `fetch_url`). Only cite prices you saw.
2. Choose a value metric (seat, usage, outcome) and justify it.
3. Propose good/better/best tiers. Model revenue for a sample customer base with `calculate`, showing expressions.

Output: ## Competitor price points (table with sources), ## Value metric, ## Proposed tiers (table: tier, price,
included, target customer), ## Revenue model, ## Risks (churn, cannibalization), ## Experiment to validate (2-week test).""",
        tools=[web_search, fetch_url, calculate],
        llm=llm,
        max_steps=12,
    )
