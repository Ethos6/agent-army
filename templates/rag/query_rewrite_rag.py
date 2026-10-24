"""Query Rewriting RAG

Users ask vague or multi-part questions. This agent first decomposes the question into atomic
sub-questions and rewrites each into keyword-rich search queries, retrieves for every one, and then
composes a single answer that addresses each part with citations.
"""
from army import Agent
from army.rag import index_folder, search_tool

META = {
    "category": "rag",
    "description": "Decomposes vague or multi-part questions into targeted searches, then answers each part with citations.",
    "example": "We're a non-profit thinking about annual Pro billing - what would we pay and what security do we get?",
}
EVALS = [{"input": "We're a non-profit on annual Pro billing: what discounts apply and is data encrypted?", "must_contain": ["50%", "20%", "AES"], "max_seconds": 180}]


def build(llm=None, docs: str = "examples/knowledge-base"):
    index = index_folder(docs)
    return Agent(
        name="query-rewrite-rag",
        instructions="""Before searching, write in your thought: the sub-questions, and 1-2 keyword queries for each.
Run `search_docs` for every query. Then answer:
## Answer  (one short paragraph per sub-question, cited [file:lines])
## Not found  (sub-questions the docs don't answer)""",
        tools=[search_tool(index)],
        llm=llm,
        max_steps=10,
    )
