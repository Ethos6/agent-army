"""Ad Copy Variants

Writes ad variants built for testing, not just rewording: each variant tests one distinct angle
(pain, outcome, social proof, urgency, objection-busting) and respects the platform's character
limits, which are checked exactly. Includes a test plan saying what each variant should teach you.
"""
from army import Agent
from army.tools import fetch_url, text_stats

META = {
    "category": "marketing",
    "description": "Testable ad variants, one angle each, within platform character limits, plus a test plan.",
    "example": "Search ads for an online bookkeeping service for freelancers",
}
EVALS = [{"input": "Social ads for a language-learning app", "must_contain": ["Angle", "Test plan"], "max_seconds": 120}]

LIMITS = "Search ads: headline <= 30 chars, description <= 90. Social: primary text ~125 visible chars, headline <= 40."


def build(llm=None, variants: str = "6"):
    return Agent(
        name="ad-variants",
        instructions=f"""You are a performance copywriter. Fetch the landing page with `fetch_url` if one is given.

Write {variants} variants. Each tests ONE angle: pain, outcome, social proof, urgency, objection, curiosity...
Limits: {LIMITS} Count characters exactly (headlines are short, so count them carefully).

For each:
### Variant N - Angle: <angle>
Headline / Description (or Primary text) / CTA
**Hypothesis:** what we learn if it wins.

## Test plan: which variants to pair, budget split, success metric, minimum sample before deciding.""",
        tools=[fetch_url, text_stats],
        llm=llm,
    )
