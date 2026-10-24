"""API Docs Writer

Reads your source code and writes developer documentation from what the code actually does: an
overview, every public function or endpoint with parameters, return values, errors and a runnable
example. It flags undocumented behaviour and inconsistencies it found, and saves the docs to
outputs/.
"""
from army import Agent
from army.tools import list_files, read_file, write_file

META = {
    "category": "engineering",
    "description": "Generates accurate reference docs with examples from your source code, and flags inconsistencies.",
    "example": "Document the public API of army/memory.py",
}
EVALS = [{"input": "Document the public API of army/rag.py", "must_contain": ["BM25Index", "outputs/"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="api-docs-writer",
        instructions="""You are a technical writer who reads code carefully. `list_files` / `read_file` the modules requested.

Document only what the code does (no guessing). For each public function, class or endpoint:
### `signature`
Description, Parameters (| name | type | default | meaning |), Returns, Raises, Example (runnable).

Add: ## Overview at the top, ## Gotchas (surprising behaviour found in code), ## Inconsistencies (naming, missing
validation). Save as Markdown with `write_file` and report the path.""",
        tools=[list_files, read_file, write_file],
        llm=llm,
    )
