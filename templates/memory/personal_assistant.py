"""Personal Assistant with Memory

An assistant that remembers you across sessions: your preferences, projects, people and goals. It
recalls relevant memories before answering, saves new lasting facts, and forgets when you correct
it. Memory is a local JSON file you can read and edit (~/.army/memory/assistant.json).
"""
from army import Agent
from army.memory import MEMORY_RULES, Memory
from army.tools import calculate
from army.web import web_search

META = {
    "category": "memory",
    "description": "Remembers your preferences, projects and goals across sessions in a local, editable memory file.",
    "example": "I'm vegetarian and I'm training for a half marathon in March. Suggest a dinner for tonight.",
}
EVALS = [{"input": "Remember that my favourite colour is teal. What is my favourite colour?", "must_contain": ["teal"], "max_seconds": 120}]


def build(llm=None, namespace: str = "assistant"):
    mem = Memory(namespace)
    return Agent(
        name="personal-assistant",
        instructions=f"""You are a thoughtful personal assistant who knows the user well.

{MEMORY_RULES}

Use what you recall to personalize every answer (mention it briefly so the user sees why). Use `web_search` for current
facts and `calculate` for numbers.""",
        tools=[*mem.tools(), web_search, calculate],
        llm=llm,
    )
