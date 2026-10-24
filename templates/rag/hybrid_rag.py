"""Hybrid Search RAG

Combines keyword search (BM25, great for exact names, codes and numbers) with semantic search
(embeddings, great for paraphrases) using reciprocal-rank fusion. Embeddings come from
ARMY_EMBED_MODEL (OpenAI, Gemini or a local Ollama model) and are computed lazily on the first
question.
"""
from army import Agent
from army.rag import HybridIndex, index_folder, search_tool

META = {
    "category": "rag",
    "description": "Keyword + embedding search fused with reciprocal-rank fusion, cited to file:line.",
    "example": "Can students get a discount, and how much?",
    "needs": "An embedding model: OPENAI_API_KEY, GEMINI_API_KEY, or Ollama with nomic-embed-text.",
}
EVALS = [{"input": "Can students get a discount, and how much?", "must_contain": ["50%"], "max_seconds": 180}]


def build(llm=None, docs: str = "examples/knowledge-base", embed_model: str = ""):
    index = HybridIndex(index_folder(docs), embed_model or None)
    return Agent(
        name="hybrid-rag",
        instructions="""Answer from the knowledge base only. `search_docs` uses hybrid keyword + semantic retrieval, so natural-
language queries work; still try a second phrasing if the first results are weak. Cite every claim [file:lines].
If the answer is not there, say "Not in the knowledge base.\"""",
        tools=[search_tool(index)],
        llm=llm,
        max_steps=6,
    )
