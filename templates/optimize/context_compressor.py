"""Context Compressor

Cuts the tokens you send to expensive models. It rewrites long documents, logs or chat histories
into dense notes that keep every fact, number, name, decision and open question while dropping
filler, then reports the compression ratio. Feed the result to a bigger model to save cost.
"""
from army import Agent
from army.tools import fetch_url, read_file, text_stats, write_file

META = {
    "category": "optimize",
    "description": "Compresses long text into dense, fact-preserving notes and reports the size reduction.",
    "example": "Compress examples/talks/keynote.vtt for later use as context",
}
EVALS = [{"input": "Compress examples/knowledge-base/pricing.md", "must_contain": ["Compression", "29"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="context-compressor",
        instructions="""Read the input (`read_file` / `fetch_url`, or the pasted text) and measure it with `text_stats`.
Rewrite it as dense notes: bullet fragments, keep ALL numbers, names, dates, decisions, constraints and open questions,
drop filler, repetition and pleasantries. Measure the result with `text_stats`. Save with `write_file` (compressed.md).
Final answer: the notes, then "Compression: <before> -> <after> words (<x>% smaller)" and anything you deliberately dropped.""",
        tools=[read_file, fetch_url, text_stats, write_file],
        llm=llm,
    )
