"""Docs Q&A

Point it at a folder of Markdown, text or code. It builds a BM25 index in memory (milliseconds, no
vector database, no embedding API) and answers questions with a citation on every claim, like
[pricing.md:3-12]. It refuses when the answer isn't in the docs, and that refusal is tested.
"""
from army import Agent
from army.rag import index_folder, search_tool

META = {
    "category": "rag",
    "description": "Chat with any folder of docs. Every claim is cited to file:line, and it refuses when the answer isn't there.",
    "example": "What is the refund window on the Pro plan?",
}
EVALS = [
    {"input": "What is the refund window on the Pro plan?", "must_contain": ["30", "pricing.md"], "max_seconds": 120},
    {"input": "Who is the CEO's favourite football team?", "must_contain": ["Not in the knowledge base"], "max_seconds": 120},
]


def build(llm=None, docs: str = "examples/knowledge-base"):
    index = index_folder(docs)
    return Agent(
        name="docs-qa",
        instructions=f"""You answer questions using ONLY the knowledge base ({len(index.chunks)} passages from {docs}).

1. Search with 2-3 different keyword phrasings before concluding anything.
2. Answer only from retrieved passages. Cite each claim with its tag, e.g. [pricing.md:3-12].
3. If the passages do not contain the answer, reply exactly "Not in the knowledge base." and say what you searched for.

Answer first, then supporting detail. Keep it short.""",
        tools=[search_tool(index)],
        llm=llm,
        max_steps=6,
    )
