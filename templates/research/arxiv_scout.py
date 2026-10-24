"""arXiv Scout

Finds the papers that matter on a topic. It runs several arXiv searches with different phrasings,
reads the abstracts, ranks papers by relevance and novelty, and explains each one in plain language
with what it contributes, how it was evaluated, and its limitations.
"""
from army import Agent
from army.web import arxiv_search

META = {
    "category": "research",
    "description": "Searches arXiv several ways, ranks papers, and explains each one's contribution and limits plainly.",
    "example": "Recent work on small language models running on phones",
}
EVALS = [{"input": "Papers on retrieval-augmented generation evaluation", "must_contain": ["arxiv.org"], "max_seconds": 180}]


def build(llm=None, papers: str = "6"):
    return Agent(
        name="arxiv-scout",
        instructions=f"""You are a research scout. Run `arxiv_search` with 3 different phrasings of the topic (synonyms,
narrower technical terms). Deduplicate, then pick the {papers} most relevant papers, favouring recent ones.

For each paper:
### <title> (<year>)
<arXiv link>
**In plain words:** what problem and what idea (2 sentences).
**Evidence:** how they evaluated it (datasets, baselines) as stated in the abstract.
**Limitations / open questions:** what the abstract doesn't show.

End with ## Reading order (which to read first and why) and ## Themes across papers.""",
        tools=[arxiv_search],
        llm=llm,
    )
