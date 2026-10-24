"""Fact Checker

Paste a claim, a post or an article. The agent splits it into individual checkable claims, looks for
independent evidence for and against each, and gives a verdict (supported, misleading, false,
unverified) with sources. It distinguishes "no evidence found" from "evidence against".
"""
from army import Agent
from army.tools import calculate, fetch_url
from army.web import web_search, wikipedia

META = {
    "category": "research",
    "description": "Splits text into checkable claims and rates each with evidence for and against, fully sourced.",
    "example": "Check: 'The Great Wall of China is visible from space with the naked eye.'",
}
EVALS = [{"input": "Check: 'Humans only use 10% of their brains.'", "must_contain": ["Verdict", "False"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="fact-checker",
        instructions="""You are a professional fact-checker. Be neutral and precise.

1. Extract each distinct factual claim (ignore opinions). If a URL is given, `fetch_url` it first.
2. For each claim, search for evidence FOR and AGAINST (`web_search`, `wikipedia`, `fetch_url` on primary sources).
   Recompute any statistics with `calculate`.
3. Verdicts: Supported / Mostly supported / Misleading (true but missing context) / False / Unverified.

For each claim:
### Claim N: "<claim>"
**Verdict:** ...
**Evidence:** 2-4 bullets with sources [URL]
**Context the reader needs:** one line

End with an overall assessment in two sentences.""",
        tools=[web_search, wikipedia, fetch_url, calculate],
        llm=llm,
        max_steps=14,
    )
