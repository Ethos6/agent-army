"""Eval Case Builder

Writes evaluation cases for any Agent Army template (or your own agent). It reads the template's
source to understand its job and output format, then proposes test inputs covering the happy path,
edge cases and must-refuse cases, with must_contain checks you can paste straight into EVALS.
"""
from army import Agent
from army.tools import list_files, read_file

META = {
    "category": "finetune",
    "description": "Reads a template's code and writes ready-to-paste EVALS: happy path, edge and must-refuse cases.",
    "example": "Write eval cases for templates/rag/docs_qa.py",
}
EVALS = [{"input": "Write eval cases for templates/starter/csv_analyst.py", "must_contain": ["EVALS", "must_contain"], "max_seconds": 180}]


def build(llm=None, cases: str = "6"):
    return Agent(
        name="eval-builder",
        instructions=f"""You are a QA engineer for LLM agents. `read_file` the template (and its sample data if referenced).
Write {cases} cases: 50% happy path, 30% edge cases (ambiguous, empty, huge, wrong format), 20% must-refuse or
must-say-unknown. must_contain should check stable facts or required headings, never exact phrasing.
Output a Python block:
```python
EVALS = [
    {{"input": "...", "must_contain": ["..."], "max_seconds": 120}},
]
```
then a table explaining what each case tests.""",
        tools=[read_file, list_files],
        llm=llm,
    )
