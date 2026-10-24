"""Real Estate Team

Helps a buyer choose a home from a listings CSV. A data analyst computes price per square foot, total
monthly cost and value scores exactly; a neighbourhood researcher gathers context for each area; and
an advisor ranks the homes for the buyer's stated needs and lists questions for viewings.
"""
from army import Agent, Pipeline
from army.tools import calculate, describe_csv, read_file
from army.web import web_search

META = {
    "category": "teams",
    "description": "Analyst, neighbourhood researcher and advisor rank listings for a buyer with exact cost math.",
    "example": "Family of four, budget 600k, want a yard and short commute; listings in examples/data/listings.csv",
}
EVALS = [{"input": "Couple, budget 500k, low HOA; examples/data/listings.csv", "must_contain": ["per sqft", "Ranking"], "max_seconds": 300}]


def build(llm=None, rate: str = "6.5"):
    analyst = Agent("data-analyst", f"""`describe_csv` and `read_file` the listings. For each: price per sqft, estimated monthly
payment (20% down, {rate}% 30-year fixed: P*r*(1+r)^n/((1+r)^n-1)), plus HOA. Compute everything with `calculate`.
Output one table.""", tools=[describe_csv, read_file, calculate], llm=llm, max_steps=16)
    research = Agent("neighbourhood-researcher", """For each neighbourhood in the table, use `web_search` for schools, commute,
amenities and price trends. Add 2-3 sourced bullets per area.""", tools=[web_search], llm=llm, max_steps=10)
    advisor = Agent("advisor", """Rank the homes for the buyer's needs:
## Ranking (| Rank | Listing | Monthly cost | Why |)
## Deal-breakers spotted  ## Questions to ask at viewings  ## Negotiation notes (days on market, price per sqft vs others)""", llm=llm)
    return Pipeline(analyst, research, advisor, name="real-estate-team")
