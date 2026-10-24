"""Travel Planning Team

A lead planner delegates to three specialists (weather and timing, sights and food research,
budget and currency) and calls them as often as it needs, then writes an itinerary that reconciles
their findings. Compare it with the single-agent Travel Planner to see what delegation adds.
"""
from army import Agent
from army.tools import calculate
from army.web import exchange_rate, weather, web_search, wikipedia

META = {
    "category": "teams",
    "description": "A lead planner delegates to weather, research and budget specialists, then writes the itinerary.",
    "example": "5 days in Mexico City for two, budget 1500 USD total, we love museums and street food",
}
EVALS = [{"input": "2 days in Rome, budget 400 EUR", "must_contain": ["Day 1", "Budget"], "max_seconds": 400}]


def build(llm=None):
    w = Agent("weather-specialist", "Report the forecast with `weather` and say which days suit outdoor vs indoor plans.", tools=[weather], llm=llm)
    r = Agent("research-specialist", "Find sights, neighbourhoods and food matching the interests with `web_search` and `wikipedia`. Group by area.",
              tools=[web_search, wikipedia], llm=llm, max_steps=10)
    b = Agent("budget-specialist", "Convert currencies with `exchange_rate` and build a daily budget table with `calculate`.",
              tools=[exchange_rate, calculate], llm=llm)
    return Agent(
        "lead-planner",
        """You lead a travel team. Delegate to the weather, research and budget specialists, then write:
## Trip at a glance  ## Day 1..N (morning / afternoon / evening; indoor plans on bad-weather days)
## Budget (from the budget specialist)  ## Bookings to make now""",
        tools=[w.as_tool("Forecast and outdoor/indoor advice for a place."),
               r.as_tool("Sights, food and neighbourhoods for given interests."),
               b.as_tool("Currency conversion and daily budget table.")],
        llm=llm,
        max_steps=10,
    )
