"""Email Writer

Describe the situation and what you want to happen. The agent drafts three emails that take
different approaches (for example "gentle nudge", "create urgency", "offer an alternative"), each
with a subject line, and explains the trade-off of each so you can pick.
"""
from army import Agent

META = {
    "category": "starter",
    "description": "Three strategically different email drafts for any situation, with subject lines and trade-offs.",
    "example": "Client is 3 weeks late paying a 4,000 USD invoice; I want payment without hurting the relationship",
}
EVALS = [{"input": "Ask my manager for Friday off next week", "must_contain": ["Subject:", "Option 1", "Option 3"], "max_seconds": 90}]


def build(llm=None):
    return Agent(
        name="email-writer",
        instructions="""You are a sharp business-communication coach.

First identify the goal, the relationship, and what could go wrong. Then write three drafts that lead to
DIFFERENT outcomes, not just different tones.

For each:
### Option N: <2-4 word strategy label>
**Best when:** one line.
**Subject:** ...
<email body: short paragraphs, one clear ask, no filler like "I hope this finds you well">
**Trade-off:** what this approach risks.

End with one line recommending an option for the situation described.""",
        llm=llm,
    )
