"""Landing Page Critic

Audits a landing page like a conversion-rate expert. It reads the page and checks the five-second
test, value proposition, proof, objections, call to action and friction, scores each area, and
gives rewritten copy for the weakest parts plus A/B tests ranked by expected impact.
"""
from army import Agent
from army.tools import fetch_url, text_stats

META = {
    "category": "marketing",
    "description": "Conversion audit of any landing page with scores, rewritten copy and ranked A/B tests.",
    "example": "Critique https://www.python.org as a landing page for new developers",
}
EVALS = [{"input": "Critique https://www.wikipedia.org as a landing page", "must_contain": ["Score", "A/B tests"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="landing-page-critic",
        instructions="""You are a conversion-rate-optimization expert. Read the page with `fetch_url`; measure copy with `text_stats`.

Score 1-10 with evidence (quote the page):
| Area | Score | Evidence | Fix |
Areas: five-second clarity, value proposition, proof (logos, numbers, testimonials), objection handling, CTA strength,
friction (form length, choices), readability.

Then: ## Rewrites (new headline x3, subheadline, CTA button text) ## A/B tests (ranked by expected impact x ease)
## Quick wins (under an hour).""",
        tools=[fetch_url, text_stats],
        llm=llm,
    )
