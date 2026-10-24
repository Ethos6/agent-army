"""Deep Research

Multi-round web research for questions that need more than one search. A planner breaks the
question into sub-questions, a researcher searches and reads sources for each (with up to 25 tool
calls), and a writer produces a long-form cited report that grades its own confidence per finding.
"""
from army import Agent, Pipeline
from army.tools import calculate, fetch_url
from army.web import web_search, wikipedia

META = {
    "category": "research",
    "description": "Planner, researcher and writer agents produce a long-form, fully cited report with confidence grades.",
    "example": "What is the current state of solid-state batteries for EVs, and when will they reach mass production?",
}
EVALS = [{"input": "How do heat pumps compare with gas furnaces on running cost in cold climates?", "must_contain": ["Sources", "Confidence"], "max_seconds": 600}]


def build(llm=None, depth: str = "25"):
    planner = Agent(
        "planner",
        """Break the research question into 4-6 specific sub-questions that together answer it, ordered so later ones
build on earlier ones. For each, list 2 search queries. Output a numbered plan only.""",
        llm=llm,
    )
    researcher = Agent(
        "researcher",
        """Execute the research plan. For every sub-question: run its searches with `web_search`, open the 2-3 most
authoritative results with `fetch_url` (prefer primary sources, official data, peer-reviewed or well-known outlets),
and record findings as: `- <finding with numbers/dates> [URL]`. Note conflicting evidence explicitly.
Use `calculate` for any derived numbers. Your final answer is the full evidence log grouped by sub-question.""",
        tools=[web_search, fetch_url, wikipedia, calculate],
        llm=llm,
        max_steps=int(depth),
    )
    writer = Agent(
        "writer",
        """Write the final report from the evidence log ONLY. Do not add facts that are not in the log.

# <Title>
## Executive summary (5 bullets)
## Findings (one section per sub-question; every claim cited [n])
## Confidence (table: Finding | Confidence high/medium/low | Why)
## Open questions
## Sources (numbered list of URLs, matching the [n] citations)""",
        llm=llm,
    )
    return Pipeline(planner, researcher, writer, name="deep-research")
