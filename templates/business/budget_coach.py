"""Budget Coach

Point it at an export of your spending (CSV with date, category, amount). It computes where the money
goes with exact sums, compares against a 50/30/20 baseline, finds the leaks (subscriptions, delivery,
impulse buys) and builds a realistic savings and debt-payoff plan. Not financial advice.
"""
from army import Agent
from army.tools import aggregate_csv, calculate, describe_csv

META = {
    "category": "business",
    "description": "Exact spending breakdown from your CSV, the leaks, and a realistic savings and debt plan.",
    "example": "Analyse examples/data/budget.csv and help me save 500 more per month",
}
EVALS = [{"input": "Analyse examples/data/budget.csv", "must_contain": ["Dining", "plan"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="budget-coach",
        instructions="""You are a friendly, non-judgmental personal finance coach.

1. `describe_csv`, then `aggregate_csv` by category (sum). Negative amounts are income.
2. Compute income, total spend, savings rate and category shares with `calculate`.
3. Compare to 50/30/20 (needs / wants / savings+debt).

Output:
## Where the money went  (table: category, amount, % of income)
## Savings rate
## Leaks  (3 specific patterns with numbers, e.g. "Food delivery x2 = 79.85")
## The plan  (3-5 changes with monthly impact; total must be computed)
## Debt  (if any: avalanche vs snowball suggestion)
_Not financial advice._""",
        tools=[describe_csv, aggregate_csv, calculate],
        llm=llm,
    )
