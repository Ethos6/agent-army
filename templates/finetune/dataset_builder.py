"""Fine-tuning Dataset Builder

Turns a folder of your documents into a fine-tuning dataset: diverse, realistic instruction/response
pairs grounded in the text (with no facts that aren't in the source), saved as chat-format JSONL that
common fine-tuning tools accept. It also writes a held-out evaluation split.
"""
from army import Agent
from army.rag import index_folder, search_tool
from army.tools import list_files, read_file, write_file

META = {
    "category": "finetune",
    "description": "Docs folder to grounded instruction/response pairs in chat JSONL, with a held-out eval split.",
    "example": "Build 20 training examples from examples/knowledge-base for a support assistant",
}
EVALS = [{"input": "Build 6 training examples from examples/knowledge-base", "must_contain": ["outputs/", ".jsonl"], "max_seconds": 300}]


def build(llm=None, docs: str = "examples/knowledge-base"):
    return Agent(
        name="dataset-builder",
        instructions="""You create fine-tuning data. Read the documents (`list_files`, `read_file`, `search_docs`).
Write diverse examples: direct questions, multi-step how-tos, edge cases, and "the docs don't say" refusals (about 10%).
Responses must only use facts in the documents and match the requested assistant persona.
Format each line as JSON: {"messages": [{"role": "system", "content": ...}, {"role": "user", "content": ...},
{"role": "assistant", "content": ...}]}
Save 85% to train.jsonl and 15% to eval.jsonl with `write_file`. Final answer: counts, file paths, 2 sample lines.""",
        tools=[list_files, read_file, search_tool(index_folder(docs)), write_file],
        llm=llm,
        max_steps=14,
    )
