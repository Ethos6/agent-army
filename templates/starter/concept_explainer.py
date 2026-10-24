"""Concept Explainer

Explains any concept at three depths (a 10-year-old, a smart newcomer, a practitioner), using
Wikipedia for grounding, one analogy that actually maps, a worked example, common misconceptions,
and a three-question quiz with answers to check understanding.
"""
from army import Agent
from army.web import wikipedia

META = {
    "category": "starter",
    "description": "Any concept explained at three depths with an analogy, worked example, misconceptions and a quiz.",
    "example": "Explain gradient descent",
}
EVALS = [{"input": "Explain compound interest", "must_contain": ["Quiz", "Misconceptions"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="concept-explainer",
        instructions="""You are a gifted teacher. Look the concept up with `wikipedia` to ground the facts, then write:

## In one sentence
## Like I'm 10  (one short paragraph, one analogy whose parts map to the real thing)
## For a smart newcomer  (key ideas, no jargon without a definition)
## For a practitioner  (precise definition, formulas or mechanics, limits)
## Worked example  (concrete numbers or a step-by-step case)
## Misconceptions  (3 common wrong beliefs and the correction)
## Quiz  (3 multiple-choice questions, answers and one-line explanations at the end)""",
        tools=[wikipedia],
        llm=llm,
    )
