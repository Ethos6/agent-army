"""Semantic RAG

Pure embedding search over your documents: questions match by meaning even when they share no words
with the text ("can I get my money back?" finds the refund policy). Uses ARMY_EMBED_MODEL and keeps
vectors in memory, so there is no vector database to run.
"""
from army import Agent
from army.rag import VectorIndex, index_folder, search_tool

META = {
    "category": "rag",
    "description": "Meaning-based retrieval with embeddings, held in memory: no vector database needed.",
    "example": "Can I get my money back if I change my mind?",
    "needs": "An embedding model: OPENAI_API_KEY, GEMINI_API_KEY, or Ollama with nomic-embed-text.",
}
EVALS = [{"input": "Can I get my money back if I change my mind on Pro?", "must_contain": ["30"], "max_seconds": 180}]


def build(llm=None, docs: str = "examples/knowledge-base", embed_model: str = ""):
    index = VectorIndex(index_folder(docs).chunks, embed_model or None)
    return Agent(
        name="semantic-rag",
        instructions="""Answer only from passages returned by `search_docs` (semantic search). Cite every claim [file:lines].
If nothing relevant is returned, say "Not in the knowledge base." """,
        tools=[search_tool(index)],
        llm=llm,
        max_steps=6,
    )
