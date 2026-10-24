"""Research Tracker with Memory

A research companion that remembers your interests and what you've already read. Each time you ask
for new papers it filters out ones you've seen, ranks the rest by your stated interests, and records
what it showed you, so every session builds on the last.
"""
from army import Agent
from army.memory import MEMORY_RULES, Memory
from army.web import arxiv_search

META = {
    "category": "memory",
    "description": "Remembers your research interests and what you've read; every search builds on the last.",
    "example": "I'm interested in efficient attention mechanisms. What's new this week?",
}
EVALS = [{"input": "I research graph neural networks for chemistry. Find me 3 papers.", "must_contain": ["arxiv.org"], "max_seconds": 240}]


def build(llm=None, namespace: str = "research"):
    mem = Memory(namespace)
    return Agent(
        name="research-tracker",
        instructions=f"""You are a research companion.

{MEMORY_RULES}

Workflow: recall the user's interests and previously shown papers -> `arxiv_search` with queries built from the
interests -> skip papers already shown -> present the best ones (title, link, why it matches) -> `remember`
"shown: <arXiv id> <title>" for each one you present.""",
        tools=[*mem.tools(), arxiv_search],
        llm=llm,
        max_steps=14,
    )
