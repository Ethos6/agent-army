"""Software Agency

A digital agency in a box for scoping software projects. A product manager writes user stories and
acceptance criteria, an architect chooses the stack and designs the system, an estimator sizes the
work with ranges, and a delivery lead writes the proposal with phases, risks and a timeline.
"""
from army import Agent, Pipeline
from army.tools import calculate
from army.web import web_search

META = {
    "category": "teams",
    "description": "PM, architect, estimator and delivery lead turn an idea into a scoped, estimated proposal.",
    "example": "A booking app for a chain of 12 physiotherapy clinics, with reminders and online payments",
}
EVALS = [{"input": "An internal tool to track office equipment loans", "must_contain": ["User stories", "Estimate", "Timeline"], "max_seconds": 400}]


def build(llm=None, day_rate: str = "600"):
    pm = Agent("product-manager", "Write the problem statement, personas, user stories with acceptance criteria, and MVP vs later scope.", llm=llm)
    architect = Agent("architect", """Choose a pragmatic stack (check current options with `web_search`), components, data model and
integrations. Include a ```mermaid architecture diagram. Prefer boring, proven technology.""", tools=[web_search], llm=llm)
    estimator = Agent("estimator", f"""Estimate each user story in days (best / likely / worst); compute PERT ((b+4l+w)/6) and totals
with `calculate`; cost at {day_rate} per day. Add 15% for QA and 10% for project management.""", tools=[calculate], llm=llm, max_steps=16)
    lead = Agent("delivery-lead", """Write the client proposal:
# Proposal: <project>
## Summary  ## User stories (MVP)  ## Architecture  ## Estimate (table + total range)
## Timeline (phases with weeks)  ## Risks and assumptions  ## Next steps""", llm=llm)
    return Pipeline(pm, architect, estimator, lead, name="software-agency")
