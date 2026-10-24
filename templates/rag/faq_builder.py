"""FAQ Builder

Reads a documentation folder and writes the FAQ your users actually need: it predicts the questions
real customers ask, answers each from the docs with citations, flags questions the docs can't answer
(content gaps), and saves the FAQ as Markdown ready for your help centre.
"""
from army import Agent
from army.rag import index_folder, search_tool
from army.tools import list_files, read_file, write_file

META = {
    "category": "rag",
    "description": "Predicts customer questions, answers them from your docs with citations, and lists content gaps.",
    "example": "Build an FAQ from examples/knowledge-base",
}
EVALS = [{"input": "Build an FAQ from examples/knowledge-base", "must_contain": ["saved", "Content gaps"], "max_seconds": 240}]


def build(llm=None, docs: str = "examples/knowledge-base"):
    return Agent(
        name="faq-builder",
        instructions=f"""You are a support-content lead. Skim the docs in {docs} (`list_files`, `read_file`).
Predict 10-15 questions customers would ask (billing, setup, security, limits, troubleshooting). For each, `search_docs`
and answer in 1-3 sentences with a citation [file:lines]. If the docs can't answer, list it under Content gaps.
Save the FAQ with `write_file` (faq.md). Final answer: the FAQ and the path.""",
        tools=[list_files, read_file, search_tool(index_folder(docs)), write_file],
        llm=llm,
        max_steps=20,
    )
