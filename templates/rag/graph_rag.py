"""Entity Graph RAG

Answers multi-hop questions ("which plan includes the feature that the security page says needs
SSO?") by building a lightweight entity graph over your documents: capitalised terms, numbers with
units and defined terms become nodes, and passages that mention them together become edges. The
agent hops entity to entity and cites every passage it used.
"""
import re
from collections import defaultdict

from army import Agent, tool
from army.rag import index_folder, search_tool

META = {
    "category": "rag",
    "description": "Builds an entity graph over your docs so the agent can answer multi-hop questions with citations.",
    "example": "Which plan has the uptime SLA, and what else does that plan include?",
}
EVALS = [{"input": "Which plan has the uptime SLA, and what else does that plan include?", "must_contain": ["Enterprise", "SSO"], "max_seconds": 180}]

ENTITY = re.compile(r"\b(?:[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*|\d+(?:\.\d+)?\s?(?:%|days?|seconds?|USD|\$))")


def build(llm=None, docs: str = "examples/knowledge-base"):
    index = index_folder(docs, lines_per_chunk=4, overlap=1)  # small passages make co-occurrence meaningful
    lowercase_words = {w for c in index.chunks for w in re.findall(r"\b[a-z][a-z]+\b", c.text)}
    mentions: dict[str, set[int]] = defaultdict(set)
    for i, c in enumerate(index.chunks):
        for e in set(m.strip() for m in ENTITY.findall(c.text)):
            if len(e) < 3 or (" " not in e and e.lower() in lowercase_words):
                continue  # skip ordinary words that are only capitalised at the start of a sentence
            mentions[e.lower()].add(i)

    @tool
    def related_entities(entity: str) -> str:
        """Entities that co-occur with the given entity in the same passages, strongest first."""
        own = mentions.get(entity.lower(), set())
        if not own:
            close = [e for e in mentions if entity.lower() in e][:10]
            return f"unknown entity. Similar: {close}" if close else "unknown entity"
        scores = {e: len(own & ids) for e, ids in mentions.items() if e != entity.lower() and own & ids}
        return ", ".join(f"{e} ({n})" for e, n in sorted(scores.items(), key=lambda x: -x[1])[:25])

    @tool
    def passages_about(entity: str) -> str:
        """All passages mentioning an entity, tagged [file:lines]."""
        ids = sorted(mentions.get(entity.lower(), set()))
        return "\n\n".join(f"[{index.chunks[i].cite}]\n{index.chunks[i].text}" for i in ids[:6]) or "none"

    return Agent(
        name="graph-rag",
        instructions=f"""You answer multi-hop questions over a document graph ({len(mentions)} entities, {len(index.chunks)} passages).
Strategy: find a starting entity with `search_docs`, then hop with `related_entities` and read with `passages_about`.
Show the hop path in your final answer (A -> B -> C) and cite every passage [file:lines].""",
        tools=[search_tool(index), related_entities, passages_about],
        llm=llm,
        max_steps=10,
    )
