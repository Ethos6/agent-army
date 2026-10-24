"""Travel Concierge with Memory

A travel assistant that learns how you like to travel (seat and hotel preferences, budget comfort,
dietary needs, pace, places you've been) and applies it automatically to every new trip, while
checking live weather and currency rates.
"""
from army import Agent
from army.memory import MEMORY_RULES, Memory
from army.tools import calculate
from army.web import exchange_rate, weather, web_search

META = {
    "category": "memory",
    "description": "Learns your travel style once and applies it to every future trip, with live weather and rates.",
    "example": "I prefer boutique hotels, window seats and slow mornings. Plan a weekend in Porto.",
}
EVALS = [{"input": "I never fly red-eyes. Plan a 2-day trip to Madrid.", "must_contain": ["Madrid"], "max_seconds": 240}]


def build(llm=None, namespace: str = "travel"):
    mem = Memory(namespace)
    return Agent(
        name="travel-concierge",
        instructions=f"""You are a personal travel concierge.

{MEMORY_RULES}

Always recall travel preferences first (hotels, flights, food, pace, budget, past trips) and apply them; say which ones
you applied. Use `weather`, `exchange_rate`, `web_search` and `calculate` for live facts and budgets.""",
        tools=[*mem.tools(), weather, exchange_rate, web_search, calculate],
        llm=llm,
        max_steps=12,
    )
