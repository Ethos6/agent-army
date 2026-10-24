"""Feed Monitor

Monitors RSS/Atom feeds (status pages, blogs, regulators, competitors' changelogs) for items that
match your watch rules, for example "outage OR incident" or "pricing", and alerts only on new
matches. It remembers what it has already alerted on, so it is safe to run every hour.
"""
from army import Agent
from army.memory import Memory
from army.web import read_feed

META = {
    "category": "always-on",
    "description": "Hourly-safe feed watcher: alerts only on new items matching your rules, never repeats.",
    "example": "Alert on anything about outages or security in https://hnrss.org/frontpage",
}
EVALS = [{"input": "Alert on anything about Python in https://hnrss.org/frontpage", "must_contain": ["Alerts"], "max_seconds": 240}]


def build(llm=None, namespace: str = "feed-monitor"):
    mem = Memory(namespace)
    remember, recall, _ = mem.tools()
    return Agent(
        name="feed-monitor",
        instructions="""You run on a schedule. The request has feed URLs and watch rules.
1. `read_feed` each feed (n=30). 2. Keep items matching the rules (judge meaning, not just keywords).
3. `recall` "alerted" and drop items already alerted. 4. `remember` "alerted: <link>" for each new alert.
Output: ## Alerts (| Severity | Item | Why it matched | Link |) or "No new alerts." """,
        tools=[read_feed, remember, recall],
        llm=llm,
        max_steps=16,
    )
