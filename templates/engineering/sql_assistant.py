"""SQL Assistant

Ask questions about a SQLite database in plain English. The agent reads the schema, writes the SQL,
runs it read-only, checks that the result makes sense, and answers with the number, the query it
used and a short explanation. Write queries are refused by the tool itself, not just the prompt.
"""

from army import Agent
from army.tools import calculate, sql_query, sql_schema

META = {
    "category": "engineering",
    "description": "Plain-English questions to read-only SQL on SQLite, with the query shown and results sanity-checked.",
    "example": "Which product category earned the most revenue in examples/data/shop.db?",
}
EVALS = [{"input": "Which country's customers placed the most orders? Use examples/data/shop.db", "must_contain": ["India", "SELECT"], "max_seconds": 120}]


def build(llm=None, db: str = "examples/data/shop.db"):
    return Agent(
        name="sql-assistant",
        instructions=f"""You are a senior analytics engineer. Default database: {db} (use another path if the user gives one).

1. Always call `sql_schema` first.
2. Write one SELECT query; run it with `sql_query`. If it errors or the result looks wrong, fix and rerun.
3. Sanity-check: row counts, NULLs, joins that could duplicate rows.

Answer:
**Answer:** the result in one sentence.
```sql
<final query>
```
**How it works:** 2-3 bullets.
**Caveats:** if any.""",
        tools=[sql_schema, sql_query, calculate],
        llm=llm,
    )
