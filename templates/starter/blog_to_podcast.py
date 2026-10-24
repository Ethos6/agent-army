"""Blog to Podcast Script

Paste a blog or article URL and get a natural two-host podcast script: a cold open, a conversation
that explains the article's ideas with examples, and a recap. It stays faithful to the source and
flags claims the article doesn't support. Pair it with the Podcast Generator template to get audio.
"""
from army import Agent
from army.tools import fetch_url

META = {
    "category": "starter",
    "description": "Turns any article URL into a faithful, natural two-host podcast script with timestamps.",
    "example": "Make a 5 minute episode from https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
}
EVALS = [{"input": "Make a 3 minute episode from https://en.wikipedia.org/wiki/Large_language_model", "must_contain": ["HOST A", "HOST B"], "max_seconds": 180}]


def build(llm=None, minutes: str = "5"):
    return Agent(
        name="blog-to-podcast",
        instructions=f"""You are a podcast producer. Fetch the article with `fetch_url`, then write a {minutes}-minute script
(about {int(float(minutes) * 150)} words) for two hosts:
- HOST A: curious, asks the questions a listener would ask.
- HOST B: explains clearly with concrete examples from the article.

Format every line as `HOST A:` or `HOST B:`. Structure: [00:00] cold open hook, [00:20] intro, main segments with
timestamps, [end] three-point recap and sign-off. Only use facts from the article; if a host speculates, they say so.
End with a `Sources` line containing the URL.""",
        tools=[fetch_url],
        llm=llm,
    )
