"""CSV Analyst

Ask a question about a spreadsheet in plain English. The agent reads the real column names first,
then gets every number from a tool (grouped sums, means, min/max and an exact calculator), so the
figures it reports are the figures in your file. File access is sandboxed to ARMY_WORKDIR.
"""
from army import Agent
from army.tools import aggregate_csv, calculate, describe_csv, list_files

META = {
    "category": "starter",
    "description": "Answers plain-English questions about a CSV with tool-computed numbers only, and shows its working.",
    "example": "Which channel drove the most revenue in examples/data/campaigns.csv?",
}
EVALS = [{"input": "Which channel drove the most revenue in examples/data/campaigns.csv?", "must_contain": ["Email"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="csv-analyst",
        instructions="""You are a careful data analyst. Answer questions about CSV files using tools, never guesses.

Rules:
- Always start with `describe_csv` so you know the real column names.
- Get every number from `aggregate_csv` or `calculate`. Never do arithmetic in your head.
- If the question is ambiguous, state the interpretation you used.

Answer format:
**Answer:** one sentence with the key number.
**How I got it:** the tool calls and columns used.
**Worth a look:** one non-obvious pattern in the data, with its number.""",
        tools=[list_files, describe_csv, aggregate_csv, calculate],
        llm=llm,
    )
