"""OKR Coach

Turns fuzzy goals into strong OKRs. It rewrites objectives to be inspiring and specific, makes key
results measurable outcomes (not task lists), flags sandbagging and vanity metrics, and adds the
leading indicators and weekly check-in questions that keep the team honest.
"""
from army import Agent

META = {
    "category": "business",
    "description": "Rewrites goals into measurable OKRs, flags vanity metrics, and adds leading indicators.",
    "example": "Our goals: improve the onboarding, get more enterprise customers, make the app faster",
}
EVALS = [{"input": "Goal: grow our newsletter", "must_contain": ["Objective", "KR1"], "max_seconds": 90}]


def build(llm=None):
    return Agent(
        name="okr-coach",
        instructions="""You are an OKR coach who has run goal-setting for high-growth companies.

For each goal the user gives:
### Objective: <qualitative, inspiring, time-bound>
- KR1 / KR2 / KR3: measurable outcomes with baseline -> target (write "baseline: unknown, measure first" if missing)
**Leading indicators:** what moves weekly before the KR moves
**Watch out:** vanity metrics, tasks disguised as KRs, or targets that are too safe

Finish with ## Critique of the original goals and ## Weekly check-in questions (4).""",
        llm=llm,
    )
