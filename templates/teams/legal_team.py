"""Legal Review Team

Three specialists review a contract in sequence: a clause analyst extracts and plainly explains every
material clause, a risk analyst rates each one against market-standard terms from your side of the
deal, and a negotiator drafts redlines and a negotiation email. Informational only, not legal advice.
"""
from army import Agent, Pipeline
from army.tools import fetch_url, read_file
from army.web import web_search

META = {
    "category": "teams",
    "description": "Clause analyst, risk analyst and negotiator review a contract and produce redlines and an email.",
    "example": "Review examples/contracts/mutual_nda.md; we are the Recipient",
}
EVALS = [{"input": "Review examples/contracts/mutual_nda.md; we are the Recipient", "must_contain": ["legal fees", "Redline", "not legal advice"], "max_seconds": 300}]


def build(llm=None):
    clauses = Agent("clause-analyst", """Read the contract (`read_file` or `fetch_url`). Produce a table of every material clause:
| # | Clause | What it says in plain English | Who it favours |
Quote exact numbers (terms, durations, amounts, venues).""", tools=[read_file, fetch_url], llm=llm)
    risk = Agent("risk-analyst", """From the side of the deal the user is on, rate each clause vs market-standard terms
(use `web_search` to check norms when unsure): | Clause | Risk High/Med/Low | Why | Market standard |.
Flag one-sided terms, unusual durations, uncapped liabilities, fee-shifting, assignment and non-solicit issues.""",
                 tools=[web_search], llm=llm)
    negotiator = Agent("negotiator", """Write the deliverable:
## Top issues (ranked)
## Redlines (| Clause | Current text | Proposed text | Rationale |)
## Fallback positions
## Negotiation email (professional, firm, under 200 words)
_This is informational and not legal advice. Have a qualified lawyer review before signing._""", llm=llm)
    return Pipeline(clauses, risk, negotiator, name="legal-team")
