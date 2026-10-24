"""Newsletter Writer

Turns a set of links, notes or feeds into an issue people actually open and read: a subject line
tested against alternatives, a sharp intro, curated items with the "so what" for your readers, and a
single call to action. It keeps a consistent structure issue to issue.
"""
from army import Agent
from army.tools import fetch_url
from army.web import read_feed

META = {
    "category": "marketing",
    "description": "Links or feeds in, a readable newsletter issue out: subject lines, intro, curated items and one CTA.",
    "example": "Write this week's issue for product managers from https://hnrss.org/frontpage",
}
EVALS = [{"input": "Issue for data engineers from https://hnrss.org/frontpage", "must_contain": ["Subject", "This week"], "max_seconds": 240}]


def build(llm=None, audience: str = ""):
    who = f"The audience is {audience}." if audience else "Infer the audience from the request."
    return Agent(
        name="newsletter-writer",
        instructions=f"""You are a newsletter editor with a loyal readership. {who}

Read feeds with `read_feed` and articles with `fetch_url`. Pick the 5-7 items most useful to the audience.

Output:
**Subject:** best option, then 2 alternatives with why
**Preview text:** under 90 chars
## This week  (3-sentence intro with a point of view)
## The items  (each: bold title, 2-3 sentences on what happened and why the reader should care, link)
## One thing to try
**CTA:** a single clear ask""",
        tools=[read_feed, fetch_url],
        llm=llm,
    )
