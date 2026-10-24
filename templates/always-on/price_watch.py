"""Price Watch

Tracks prices or plan changes on pages you care about (competitor pricing pages, products, travel
fares). Each run it reads the pages, extracts the current prices, compares them with the last values
it remembered, and reports only the changes, with percentage moves calculated exactly.
"""
from army import Agent
from army.memory import Memory
from army.tools import calculate, fetch_url

META = {
    "category": "always-on",
    "description": "Scheduled price and plan tracker: remembers last values, reports only changes with exact % moves.",
    "example": "Track the plan prices on https://www.example.com/pricing",
}
EVALS = [{"input": "Track the prices on https://www.python.org/psf/sponsorship/", "must_contain": ["python.org"], "max_seconds": 240}]


def build(llm=None, namespace: str = "price-watch"):
    mem = Memory(namespace)
    remember, recall, forget = mem.tools()
    return Agent(
        name="price-watch",
        instructions="""You run on a schedule. For each URL in the request:
1. `fetch_url` and extract every price or plan with its exact value as shown.
2. `recall` "price <url>" for previous values.
3. Compare; compute changes with `calculate` ((new-old)/old*100).
4. `forget` outdated items and `remember` "price <url> <item>: <value> on <date>".
Output: ## Changes (| Page | Item | Old | New | Change % |) or "No changes", then ## Current prices.""",
        tools=[fetch_url, remember, recall, forget, calculate],
        llm=llm,
        max_steps=16,
    )
