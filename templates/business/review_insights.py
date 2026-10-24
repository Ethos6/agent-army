"""Customer Review Insights

Reads a CSV of customer feedback (reviews, survey answers, support tickets), groups it into themes,
counts how often each theme appears and how it affects ratings, tracks whether themes are getting
better or worse over time, and turns it into a prioritized fix list with representative quotes.
"""
from army import Agent
from army.tools import aggregate_csv, calculate, describe_csv, read_file

META = {
    "category": "business",
    "description": "Themes, counts, rating impact and trends from a feedback CSV, turned into a prioritized fix list.",
    "example": "What should we fix first? examples/data/reviews.csv",
}
EVALS = [{"input": "Analyse examples/data/reviews.csv", "must_contain": ["export", "Android"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="review-insights",
        instructions="""You are a voice-of-customer analyst.

1. `describe_csv` then `read_file` to see every row. Use `aggregate_csv` for rating stats by channel.
2. Tag every row with 1-2 themes. Count rows per theme and average rating per theme with `calculate`.
3. Compare first half vs second half of the date range to see if a theme is rising or falling.

Output:
## Themes  (| Theme | Mentions | Avg rating | Trend | Representative quote |)
## Fix first  (top 3, with the evidence)
## What customers love  (protect these)
## Data caveats""",
        tools=[describe_csv, read_file, aggregate_csv, calculate],
        llm=llm,
    )
