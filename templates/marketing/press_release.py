"""Press Release Writer

Writes a news-ready press release in standard format: headline, dateline, inverted-pyramid lead,
supporting facts, a spokesperson quote that says something real, boilerplate and media contact
placeholders. It also drafts a short pitch email to journalists and flags any claim needing proof.
"""
from army import Agent
from army.tools import fetch_url

META = {
    "category": "marketing",
    "description": "Standard-format press release, a journalist pitch email, and a list of claims that need proof.",
    "example": "We raised a 5M seed round to build AI bookkeeping for restaurants; launching in 3 cities",
}
EVALS = [{"input": "Our bakery opens a second location downtown on 1 November", "must_contain": ["FOR IMMEDIATE RELEASE", "Pitch email"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="press-release",
        instructions="""You are a PR director. Read any URL given with `fetch_url`.

Output:
FOR IMMEDIATE RELEASE
**Headline** (under 100 chars) / *Subheadline*
CITY, Date - lead paragraph answering who, what, when, where, why.
2-3 paragraphs of supporting detail and numbers.
One quote from a spokesperson that adds insight (no "we are thrilled").
## About <company>  (boilerplate)
## Media contact  ([Name], [Email], [Phone] placeholders)
### Pitch email  (subject + 80-word pitch)
### Claims to verify before sending""",
        tools=[fetch_url],
        llm=llm,
    )
