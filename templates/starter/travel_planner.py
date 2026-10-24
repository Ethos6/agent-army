"""Travel Planner

Builds a day-by-day itinerary from your destination, dates, budget and interests. It checks the live
7-day forecast, converts your budget into local currency, researches sights and neighbourhoods, and
puts rainy-day options on days with a high chance of rain.
"""
from army import Agent
from army.tools import calculate
from army.web import exchange_rate, weather, web_search, wikipedia

META = {
    "category": "starter",
    "description": "Day-by-day itinerary that uses the live forecast, your budget in local currency, and researched sights.",
    "example": "4 days in Lisbon next week, budget 900 USD, I love food markets and viewpoints",
}
EVALS = [{"input": "3 days in Kyoto, budget 600 USD, temples and food", "must_contain": ["Day 1", "Day 3", "budget"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="travel-planner",
        instructions="""You are an expert travel planner who plans realistic days, not wish lists.

Method:
1. Call `weather` for the destination. Note days with rain chance above 50%.
2. If a budget is given in another currency, convert it with `exchange_rate`; do all sums with `calculate`.
3. Use `web_search` / `wikipedia` to find sights, food and neighbourhoods that match the traveller's interests.
4. Group nearby places on the same day. Max 3 major stops per day.

Output (Markdown):
## Trip at a glance  (dates, weather summary, budget in both currencies)
## Day 1 ... Day N  (morning / afternoon / evening, each with a one-line why; put indoor options on rainy days)
## Budget  (table: lodging, food, transport, activities, buffer; total must not exceed the budget)
## Practical tips  (transport pass, booking-ahead items, local etiquette)""",
        tools=[weather, exchange_rate, web_search, wikipedia, calculate],
        llm=llm,
        max_steps=14,
    )
