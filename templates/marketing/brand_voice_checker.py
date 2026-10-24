"""Brand Voice Checker

Checks a draft against your brand voice. It learns the voice from your existing pages or a
guidelines file, scores the draft on each voice attribute with quoted evidence, flags banned or
off-brand phrases, and returns a corrected version with every change explained.
"""
from army import Agent
from army.tools import fetch_url, read_file

META = {
    "category": "marketing",
    "description": "Learns your voice from your pages or guide, scores a draft against it, and fixes off-brand lines.",
    "example": "Check this against the voice of https://www.python.org: 'Unlock synergies with our revolutionary paradigm!'",
}
EVALS = [{"input": "Voice: friendly, plain, no hype. Check: 'Leverage our cutting-edge, best-in-class solution today!'", "must_contain": ["Score", "Revised"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="brand-voice-checker",
        instructions="""You are a brand editor. Learn the voice from what the user provides: a description, a guidelines file
(`read_file`), or example pages (`fetch_url`). Summarise it as 4-6 attributes with "this, not that" pairs.

Then for the draft:
## Voice profile
## Score  (| Attribute | Score 1-5 | Evidence from the draft |)
## Off-brand phrases  (quote, why, replacement)
## Revised draft
## Change log""",
        tools=[read_file, fetch_url],
        llm=llm,
    )
