"""Chat with a Newsletter or Blog

Most newsletters and blogs publish an RSS feed (for example https://<name>.substack.com/feed). This
agent reads the archive from the feed, opens full posts when needed, and answers questions across
issues: "what has the author said about pricing?", "summarize the last month".
"""
from army import Agent
from army.tools import fetch_url
from army.web import read_feed

META = {
    "category": "chat",
    "description": "Ask questions across a newsletter's or blog's archive via its RSS feed, with links to each post.",
    "example": "From https://hnrss.org/frontpage, which stories are about databases?",
}
EVALS = [{"input": "Summarize the latest posts at https://hnrss.org/frontpage", "must_contain": ["http"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="chat-with-newsletter",
        instructions="""Read the feed with `read_feed` (n=30). Open full posts with `fetch_url` when summaries aren't enough.
Answer across posts, citing each post's title and link. Note dates so the user can see how views evolved.""",
        tools=[read_feed, fetch_url],
        llm=llm,
        max_steps=8,
    )
