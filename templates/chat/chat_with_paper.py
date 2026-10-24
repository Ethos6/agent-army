"""Chat with a Research Paper

Discuss a research paper conversationally. Give an arXiv ID, link or title; the agent finds it, reads
the abstract and the full HTML version when available, and answers questions about the method,
results, assumptions and limitations, separating what the paper claims from what it shows.
"""
from army import Agent
from army.tools import fetch_url
from army.web import arxiv_search

META = {
    "category": "chat",
    "description": "Discuss any arXiv paper: method, results, assumptions and limits, claims vs evidence.",
    "example": "Explain the method in 'Attention Is All You Need' and its main limitation",
}
EVALS = [{"input": "What problem does the paper 'Attention Is All You Need' solve?", "must_contain": ["Transformer"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="chat-with-paper",
        instructions="""Find the paper with `arxiv_search` (by title or ID). Read the full text when available with `fetch_url`
on https://arxiv.org/html/<id> (fall back to https://arxiv.org/abs/<id>).
Answer the user's questions precisely, citing sections. Distinguish "the paper claims" from "the experiments show".
Explain jargon on first use.""",
        tools=[arxiv_search, fetch_url],
        llm=llm,
        max_steps=8,
    )
