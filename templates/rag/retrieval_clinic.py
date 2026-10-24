"""Retrieval Clinic

Diagnoses why a RAG system gives bad answers. Give it a few questions and the expected answers; it
runs retrieval for each, inspects the ranked passages and scores, and classifies each failure
(missing content, chunking split, vocabulary mismatch, ranking noise, ambiguous question) with a
concrete fix.
"""
from army import Agent, tool
from army.rag import index_folder

META = {
    "category": "rag",
    "description": "Runs your test questions through retrieval and diagnoses each failure type with a fix.",
    "example": "Q: refund window for Pro? expected: 30 days. Q: SSO on which plan? expected: Enterprise. Q: SOC 2 report? expected: unknown",
}
EVALS = [{"input": "Q: SSO on which plan? expected: Enterprise. Q: Do you have a SOC 2 report? expected: not documented", "must_contain": ["Diagnosis", "missing content"], "max_seconds": 180}]


def build(llm=None, docs: str = "examples/knowledge-base"):
    index = index_folder(docs)

    @tool
    def inspect_retrieval(query: str, k: int = 5) -> str:
        """Run retrieval and show ranked passages with BM25 scores, chunk boundaries and matched terms."""
        from army.rag import tokenize

        hits = index.search(query, int(k))
        if not hits:
            return f"NO RESULTS. Query terms: {tokenize(query)}"
        terms = set(tokenize(query))
        return "\n\n".join(
            f"#{i} score={s:.2f} [{c.cite}] matched={sorted(terms & set(tokenize(c.text)))}\n{c.text[:400]}"
            for i, (s, c) in enumerate(hits, 1)
        )

    return Agent(
        name="retrieval-clinic",
        instructions=f"""You are a RAG reliability engineer. The index has {len(index.chunks)} chunks from {docs}.
For each test question: run `inspect_retrieval` (also try one rephrasing), compare with the expected answer.

Classify: OK / missing content / chunking split / vocabulary mismatch / ranking noise / ambiguous question.
Output: | Question | Top hit | Contains answer? | Diagnosis | Fix |, then ## Systemic fixes (chunk size, synonyms,
hybrid search, content to add).""",
        tools=[inspect_retrieval],
        llm=llm,
        max_steps=12,
    )
