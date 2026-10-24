"""Chat with a Website

Ask questions about any website. The agent reads the home page and the most relevant linked pages on
the same domain (docs, pricing, about, FAQ), then answers with the URL each fact came from. Useful
for vendor evaluations, support questions and quick research.
"""
from army import Agent
from army.tools import fetch_url
from army.web import crawl_site

META = {
    "category": "chat",
    "description": "Answers questions about any site by reading its relevant pages, citing the URL for each fact.",
    "example": "Does https://www.python.org offer an official beginner's guide, and where?",
}
EVALS = [{"input": "What is https://www.python.org/psf/ and what does it do?", "must_contain": ["Python Software Foundation"], "max_seconds": 180}]


def build(llm=None, pages: str = "6"):
    return Agent(
        name="chat-with-website",
        instructions=f"""Answer questions about the website in the request. Use `crawl_site` (max_pages={pages}) to explore, and
`fetch_url` for specific pages you spot in links. Cite the URL after each fact. If the site doesn't say, say so.""",
        tools=[crawl_site, fetch_url],
        llm=llm,
        max_steps=8,
    )
