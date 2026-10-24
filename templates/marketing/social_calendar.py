"""Social Media Calendar

Plans a month of social posts across channels from your goals and source material. It balances
content pillars, adapts each post to the channel's format, writes the copy, and saves the calendar
as a CSV you can import into a scheduler.
"""
from army import Agent
from army.tools import fetch_url, write_file

META = {
    "category": "marketing",
    "description": "A month of channel-native posts across content pillars, written and saved as an importable CSV.",
    "example": "4-week calendar for a yoga studio on Instagram and LinkedIn, goal: more class sign-ups",
}
EVALS = [{"input": "2-week calendar for a coffee roaster on Instagram", "must_contain": ["Week 1", "saved"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="social-calendar",
        instructions="""You are a social media manager. If URLs are given, read them with `fetch_url` for material.

1. Define 3-4 content pillars tied to the goal (educate, prove, entertain, convert) with a target mix.
2. Plan the requested weeks: per channel, realistic frequency; adapt format (carousel, short video script, text post).
3. Write full copy for every post (hook first line, body, CTA, max 3 relevant hashtags).

Save a CSV with columns date,channel,pillar,format,copy,cta via `write_file` (social_calendar.csv).
Then show a Markdown overview by week (Week 1, Week 2...) and the file path.""",
        tools=[fetch_url, write_file],
        llm=llm,
    )
