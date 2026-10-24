"""Link Summarizer

Give it one or more links and get a TL;DR, the key points, notable numbers, and who should read the
original. It quotes sparingly and marks anything that is the author's opinion rather than fact.
"""
from army import Agent
from army.tools import fetch_url

META = {
    "category": "starter",
    "description": "TL;DR, key points, numbers and 'should I read it?' for any link or list of links.",
    "example": "Summarize https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)",
}
EVALS = [{"input": "Summarize https://en.wikipedia.org/wiki/Prompt_engineering", "must_contain": ["TL;DR", "Key points"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="url-summarizer",
        instructions="""Fetch every link with `fetch_url`. For each one write:

### <title>
**TL;DR:** two sentences.
**Key points:** 3-6 bullets.
**Numbers worth knowing:** figures with their context (skip if none).
**Opinion vs fact:** note claims that are the author's opinion.
**Read the original if:** one line on who benefits from the full piece.

If several links are given, finish with **How they relate** (agreements, contradictions).""",
        tools=[fetch_url],
        llm=llm,
    )
