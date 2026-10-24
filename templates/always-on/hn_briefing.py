"""Daily Hacker News Briefing

A scheduled scout for your interests. Each run it reads the Hacker News front page, skips stories it
already sent you (tracked in memory), ranks the rest for your interests, and writes a short brief.
Run it daily and post to a Slack, Discord or Teams webhook:
army schedule hn-briefing "AI infra and databases" --every 1440 --webhook $WEBHOOK_URL
"""
from army import Agent
from army.memory import Memory
from army.tools import fetch_url
from army.web import hacker_news

META = {
    "category": "always-on",
    "description": "A scheduled scout: ranks new Hacker News stories for your interests, never repeats one, posts to a webhook.",
    "example": "AI infrastructure, databases and developer tools",
}
EVALS = [{"input": "Python and data engineering", "must_contain": ["Today's picks"], "max_seconds": 300}]


def build(llm=None, stories: str = "40", namespace: str = "hn-briefing"):
    mem = Memory(namespace)
    remember, recall, _ = mem.tools()
    return Agent(
        name="hn-briefing",
        instructions=f"""You run on a schedule. The request is the reader's interests.
1. `recall` with query "sent" and k=200 to get ALL stories already sent.  2. `hacker_news` (n={stories}).  3. Drop already-sent stories.
4. Pick up to 7 that match the interests; open 1-2 with `fetch_url` if the title is ambiguous.
5. `remember` "sent: <title>" for each story you include.
Output: ## Today's picks (title, 1-line why it matters, link, points/comments) and ## Also trending (3 one-liners).
If nothing new matches, say "Nothing new worth your time today." """,
        tools=[remember, recall, hacker_news, fetch_url],
        llm=llm,
        max_steps=16,
    )
