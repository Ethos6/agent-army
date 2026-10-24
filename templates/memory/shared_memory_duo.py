"""Shared-Memory Duo

Two agents, optionally on different models, share one memory store. A planner records decisions and
open questions as it works; an executor recalls them and builds on them in the same or a later
session. It shows how a team of different models keeps one consistent picture of a project.
"""
from army import Agent, Pipeline, get_llm
from army.memory import MEMORY_RULES, Memory

META = {
    "category": "memory",
    "description": "A planner and an executor, possibly on different models, share one memory of the project.",
    "example": "We're launching a podcast for indie founders. Plan the first month and draft episode 1's outline.",
}
EVALS = [{"input": "Plan a small team offsite for 8 people and draft the agenda", "must_contain": ["Agenda"], "max_seconds": 240}]


def build(llm=None, namespace: str = "project", planner_model: str = "", executor_model: str = ""):
    mem = Memory(namespace)
    planner = Agent("planner", f"""You plan. {MEMORY_RULES}
Recall project context, make the plan, and `remember` each key decision and open question (one per call).
Output the plan.""", tools=mem.tools(), llm=get_llm(planner_model) if planner_model else llm, max_steps=12)
    executor = Agent("executor", f"""You execute. {MEMORY_RULES}
`recall` the decisions the planner stored, then produce the requested deliverable consistent with them, and `remember`
what you produced. List which remembered decisions you followed.""", tools=mem.tools(),
                     llm=get_llm(executor_model) if executor_model else llm, max_steps=12)
    return Pipeline(planner, executor, name="shared-memory-duo")
