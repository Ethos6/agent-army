"""Meal Planner

Plans a week of meals around your diet, time and budget, reuses ingredients across days to cut
waste, and produces a consolidated shopping list grouped by aisle with estimated cost. Quantities
and totals are calculated exactly.
"""
from army import Agent
from army.tools import calculate

META = {
    "category": "starter",
    "description": "A week of meals that reuse ingredients, plus an aisle-grouped shopping list with exact totals.",
    "example": "Vegetarian, 2 people, 30 minutes max on weekdays, budget 80 USD per week",
}
EVALS = [{"input": "High-protein, 1 person, budget 60 USD", "must_contain": ["Monday", "Shopping list"], "max_seconds": 120}]


def build(llm=None, days: str = "7"):
    return Agent(
        name="meal-planner",
        instructions=f"""You are a practical home-cooking planner. Plan {days} days (breakfast, lunch, dinner) that respect the diet,
allergies, time limits and budget given.

Rules: reuse perishable ingredients across at least two meals; batch-cook once; use `calculate` for every quantity
and cost sum; keep estimated cost within budget.

Output:
## Plan  (table: Day | Breakfast | Lunch | Dinner | Prep minutes)
## Shopping list  (grouped by aisle: produce, protein, dairy, pantry...; quantity and estimated price each)
## Total estimated cost
## Batch-prep plan  (what to cook on day 1 and how to store it)""",
        tools=[calculate],
        llm=llm,
    )
