"""Literature Review Matrix

Produces a structured literature review: a comparison matrix of papers (method, data, metric,
result, limitation), a synthesis of where the field agrees and disagrees, and research gaps worth
pursuing. Built for students and R&D teams starting a new topic.
"""
from army import Agent
from army.tools import write_file
from army.web import arxiv_search, web_search

META = {
    "category": "research",
    "description": "A paper-by-paper comparison matrix, synthesis of agreements and conflicts, and research gaps.",
    "example": "Literature review on LLM hallucination detection methods",
}
EVALS = [{"input": "Literature review on federated learning for healthcare", "must_contain": ["| Paper", "Gaps"], "max_seconds": 300}]


def build(llm=None):
    return Agent(
        name="literature-review",
        instructions="""You are a meticulous academic reviewer.

1. Search with `arxiv_search` (3+ phrasings) and `web_search` for surveys or benchmark pages.
2. Select 6-10 papers. Use only what abstracts and pages state.

Output:
## Scope  (question, inclusion criteria)
## Matrix  (| Paper (year, link) | Method | Data | Metric | Reported result | Limitation |)
## Synthesis  (where results agree, where they conflict and possible reasons)
## Gaps  (3-5 concrete open research questions)
## Suggested next reads
Also save the matrix as CSV with `write_file` (literature_matrix.csv) and mention the path.""",
        tools=[arxiv_search, web_search, write_file],
        llm=llm,
        max_steps=14,
    )
