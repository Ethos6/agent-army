"""Dashboard Builder

Describe the dashboard you want and point it at a CSV. The agent computes the real numbers with
tools, then generates a single self-contained HTML file (no external libraries) with KPI tiles,
SVG bar and line charts and a data table, saved to outputs/ so you can open it in any browser or
share it.
"""
from army import Agent
from army.tools import aggregate_csv, calculate, describe_csv, write_file

META = {
    "category": "ui",
    "description": "CSV plus a plain-English description in, a self-contained HTML dashboard with real numbers out.",
    "example": "Build a marketing dashboard from examples/data/campaigns.csv: revenue and signups by channel and month",
}
EVALS = [{"input": "Dashboard of spend and revenue by channel from examples/data/campaigns.csv", "must_contain": ["saved", ".html"], "max_seconds": 300}]


def build(llm=None):
    return Agent(
        name="dashboard-builder",
        instructions="""You build data dashboards as single HTML files.

1. `describe_csv`, then compute every figure with `aggregate_csv` / `calculate`. Never invent numbers.
2. Write ONE self-contained HTML file: inline CSS, inline SVG charts drawn from your computed numbers (bars: <rect>,
   lines: <polyline>), no external scripts or fonts. Include: title, 3-4 KPI tiles, 2 charts with axis labels and
   values, a summary table. Responsive layout, readable in light and dark mode (prefers-color-scheme).
3. Save with `write_file` (dashboard.html).
Final answer: the path and a list of the figures shown with their values.""",
        tools=[describe_csv, aggregate_csv, calculate, write_file],
        llm=llm,
        max_steps=14,
    )
