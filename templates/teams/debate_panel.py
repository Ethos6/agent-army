"""Debate Panel

Stress-tests a decision or claim through structured debate. An advocate builds the strongest case
for, a critic builds the strongest case against (both with web evidence), and a neutral moderator
weighs the arguments, identifies the cruxes and gives a verdict with its confidence. Each side can
run on a different model with --opt models=a,b,c.
"""
from army import Agent, Pipeline, get_llm
from army.web import web_search

META = {
    "category": "teams",
    "description": "Advocate and critic argue with evidence; a moderator finds the cruxes and rules. Mix models freely.",
    "example": "Should our 20-person startup move from a monolith to microservices?",
}
EVALS = [{"input": "Should cities ban cars from downtown areas?", "must_contain": ["Cruxes", "Verdict"], "max_seconds": 400}]


def build(llm=None, models: str = ""):
    specs = [s.strip() for s in models.split(",")] if models else []
    pick = lambda i: get_llm(specs[i]) if len(specs) > i and specs[i] else llm
    advocate = Agent("advocate", "Build the strongest evidence-based case FOR the proposition. Use `web_search`; cite sources. 5 arguments max.",
                     tools=[web_search], llm=pick(0))
    critic = Agent("critic", """Build the strongest evidence-based case AGAINST the proposition, and rebut the advocate's points
directly. Use `web_search`; cite sources. Keep the advocate's case in your output, then add yours.""", tools=[web_search], llm=pick(1))
    moderator = Agent("moderator", """You are a neutral moderator. Output:
## Strongest argument for / against  ## Cruxes (what the disagreement really hinges on)
## Verdict (and confidence low/medium/high)  ## What evidence would change the verdict""", llm=pick(2))
    return Pipeline(advocate, critic, moderator, name="debate-panel")
