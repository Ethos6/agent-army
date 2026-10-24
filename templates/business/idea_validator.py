"""Startup Idea Validator

Stress-tests a startup idea before you spend months on it. It searches for existing competitors and
failed attempts, estimates who has the problem and how painful it is, scores the idea, and designs
the cheapest experiments to prove or kill it within two weeks.
"""
from army import Agent
from army.tools import calculate, fetch_url
from army.web import hacker_news, web_search

META = {
    "category": "business",
    "description": "Finds competitors and past failures, scores the idea, and designs 2-week kill-or-prove tests.",
    "example": "An app that books last-minute restaurant cancellations for a fee",
}
EVALS = [{"input": "A marketplace for renting camping gear between neighbours", "must_contain": ["Competitors", "Experiments"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="idea-validator",
        instructions="""You are a skeptical but constructive startup advisor.

1. `web_search` for direct competitors, adjacent solutions, and failed startups that tried this (search "shut down", "post-mortem").
2. Identify the customer, the job-to-be-done, and current workaround.

Output:
## The idea in one line
## Competitors and alternatives  (table with links)
## Why previous attempts failed  (if found)
## Scorecard  (pain, frequency, willingness to pay, distribution, competition: 1-5 each, with reasons; total via `calculate`)
## Riskiest assumption
## Experiments  (3 tests under 2 weeks each, with pass/fail thresholds)""",
        tools=[web_search, fetch_url, hacker_news, calculate],
        llm=llm,
        max_steps=12,
    )
