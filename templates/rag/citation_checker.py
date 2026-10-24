"""Citation-Checked RAG

Two agents keep each other honest. An answerer writes a cited answer from the docs; a verifier then
re-retrieves every cited passage and checks that it really supports the sentence it's attached to,
removing or correcting anything unsupported. You get the verified answer and an audit table.
"""
from army import Agent, Pipeline
from army.rag import index_folder, search_tool

META = {
    "category": "rag",
    "description": "An answerer cites the docs; a verifier re-checks every citation and strips unsupported claims.",
    "example": "Summarize our refund and discount policies",
}
EVALS = [{"input": "Summarize the refund and discount policies", "must_contain": ["Verified answer", "Audit"], "max_seconds": 240}]


def build(llm=None, docs: str = "examples/knowledge-base"):
    search = search_tool(index_folder(docs))
    answerer = Agent("answerer", "Answer from `search_docs` results only. Put a [file:lines] citation after every sentence.",
                     tools=[search], llm=llm, max_steps=6)
    verifier = Agent("verifier", """You audit a cited answer. For every sentence, search for its cited passage with `search_docs` and
judge: SUPPORTED / PARTIAL / UNSUPPORTED. Remove unsupported claims; fix partial ones.
Output: ## Verified answer, then ## Audit (| Sentence | Citation | Verdict |).""", tools=[search], llm=llm, max_steps=10)
    return Pipeline(answerer, verifier, name="citation-checker")
