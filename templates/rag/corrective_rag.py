"""Corrective RAG

Retrieval that checks itself before answering. After each search it grades every passage as
relevant, partial or irrelevant; if the evidence is weak it rewrites the query and searches again,
and as a last resort falls back to web search, clearly labelling which facts came from the web.
"""
from army import Agent
from army.rag import index_folder, search_tool
from army.web import web_search

META = {
    "category": "rag",
    "description": "Grades its own retrieved passages, retries with better queries, and falls back to the web, labelled.",
    "example": "How do I rotate an API key, and how quickly do revoked keys stop working?",
}
EVALS = [{"input": "How quickly do revoked API keys stop working?", "must_contain": ["60", "security.md"], "max_seconds": 180}]


def build(llm=None, docs: str = "examples/knowledge-base", web_fallback: str = "yes"):
    index = index_folder(docs)
    tools = [search_tool(index)] + ([web_search] if web_fallback == "yes" else [])
    return Agent(
        name="corrective-rag",
        instructions="""You are a careful retrieval agent that corrects itself.

Loop (max 3 rounds):
1. `search_docs` with a precise query.
2. Grade each passage: RELEVANT / PARTIAL / IRRELEVANT (write the grades in your thought).
3. If no passage is RELEVANT, rewrite the query (synonyms, narrower terms) and search again.
If still insufficient and web search is available, use `web_search` and mark those facts with [web].

Final answer: the answer with citations ([file:lines] or [web: URL]), then a line "Retrieval: <rounds> rounds,
<n> relevant passages".""",
        tools=tools,
        llm=llm,
        max_steps=8,
    )
