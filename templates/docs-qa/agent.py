from pathlib import Path

from army import Agent
from army.rag import BM25Index, search_tool

REPO = Path(__file__).resolve().parents[2]


def build(llm=None, docs: str = "examples/knowledge-base"):
    folder = Path(docs) if Path(docs).exists() else REPO / docs
    if not folder.is_dir():
        raise FileNotFoundError(f"docs folder not found: {docs}")
    index = BM25Index.from_folder(folder)
    return Agent(
        name="docs-qa",
        instructions=f"""You answer questions using ONLY the knowledge base ({len(index.chunks)} passages indexed from {docs}).

Method:
1. Search with 2-3 different keyword phrasings before concluding anything.
2. Answer only from retrieved passages. Cite each claim with its tag, e.g. [pricing.md:3-12].
3. If the passages do not contain the answer, reply exactly: "Not in the knowledge base." and say what you searched for.

Keep answers short: the answer first, then supporting detail.""",
        tools=[search_tool(index)],
        llm=llm,
        max_steps=6,
    )
