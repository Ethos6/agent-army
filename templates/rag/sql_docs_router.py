"""Database + Docs Router

Some questions need numbers from a database, others need policy from documents, and some need
both ("how much did India spend, and do they qualify for a discount?"). This agent decides per
question whether to query SQL (read-only), search the docs, or combine them, and cites both kinds of
evidence.
"""
from army import Agent
from army.rag import index_folder, search_tool
from army.tools import calculate, sql_query, sql_schema

META = {
    "category": "rag",
    "description": "Routes each question to read-only SQL, document search, or both, and cites each kind of evidence.",
    "example": "How many orders did customers in India place, and what annual-billing discount could they get?",
}
EVALS = [{"input": "How many orders did customers in India place, and what is the annual billing discount?", "must_contain": ["4", "20%"], "max_seconds": 180}]


def build(llm=None, db: str = "examples/data/shop.db", docs: str = "examples/knowledge-base"):
    return Agent(
        name="sql-docs-router",
        instructions=f"""You have a SQLite database ({db}) and a document store. Decide per sub-question:
- numbers, counts, records -> `sql_schema` then `sql_query` (read-only)
- policies, how-to, definitions -> `search_docs`
Combine when needed; use `calculate` for derived numbers.
Answer with: the answer, then Evidence: SQL used (code block) and doc citations [file:lines].""",
        tools=[sql_schema, sql_query, search_tool(index_folder(docs)), calculate],
        llm=llm,
        max_steps=10,
    )
