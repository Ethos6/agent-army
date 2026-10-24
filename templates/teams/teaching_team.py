"""Teaching Team

A faculty of agents builds a personal learning path: a curriculum designer sequences the topic into
modules, a librarian finds high-quality free resources for each, an explainer writes the key ideas,
and an assessor writes practice exercises and a study schedule that fits your available hours.
"""
from army import Agent, Pipeline
from army.web import web_search, wikipedia

META = {
    "category": "teams",
    "description": "Curriculum designer, librarian, explainer and assessor build a personal learning path.",
    "example": "Teach me SQL for data analysis in 4 weeks, 5 hours a week, I know Excel",
}
EVALS = [{"input": "Teach me the basics of statistics in 2 weeks", "must_contain": ["Module 1", "Schedule"], "max_seconds": 400}]


def build(llm=None):
    designer = Agent("curriculum-designer", """Assess the learner's starting point and goal, then design 4-6 modules in order,
each with learning outcomes and prerequisites.""", llm=llm)
    librarian = Agent("librarian", """For each module, find 2-3 free, high-quality resources with `web_search` (official docs,
university courses, respected tutorials). Give links and why each is good.""", tools=[web_search], llm=llm, max_steps=12)
    explainer = Agent("explainer", """For each module write a short primer of the key ideas (check facts with `wikipedia`),
with one worked example.""", tools=[wikipedia], llm=llm)
    assessor = Agent("assessor", """Produce the final learning path:
## Module 1..N (outcomes, primer, resources, 3 practice exercises with answers at the end)
## Schedule (week-by-week within the learner's hours)
## Capstone project""", llm=llm)
    return Pipeline(designer, librarian, explainer, assessor, name="teaching-team")
