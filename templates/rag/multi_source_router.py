"""Multi-Source Router

Answers across several separate knowledge bases (for example product docs, HR policies and
engineering wikis). Each source gets its own search tool; the agent routes each question to the
right one, searches more than one when the question spans them, and says which source every fact
came from.
"""
from army import Agent
from army.rag import index_folder, search_tool

META = {
    "category": "rag",
    "description": "Routes each question to the right knowledge base among several, citing source and file:line.",
    "example": "What does Pro cost, and how many remote days a week can employees work?",
}
EVALS = [{"input": "What does Pro cost, and how many days of annual leave do employees get?", "must_contain": ["29", "24"], "max_seconds": 180}]


def build(llm=None, sources: str = "product=examples/knowledge-base,hr=examples/hr-policies"):
    tools, names = [], []
    for pair in sources.split(","):
        name, _, folder = pair.partition("=")
        name = name.strip().replace("-", "_")
        tools.append(search_tool(index_folder(folder.strip()), name=f"search_{name}"))
        names.append(name)
    return Agent(
        name="multi-source-router",
        instructions=f"""You route questions across these knowledge bases: {', '.join(names)}.
Pick the most likely source by name; search others if the question spans topics or the first source has nothing.
Cite as [source: file:lines]. If none contain the answer, say so.""",
        tools=tools,
        llm=llm,
        max_steps=8,
    )
