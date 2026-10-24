"""Journal Coach

A reflective journaling partner that remembers your goals, recurring themes and past entries. It
asks one good question at a time, notices patterns across weeks ("this is the third time deadlines
came up"), and suggests small next steps. It is supportive, not a therapist, and points to
professional help when something sounds serious.
"""
from army import Agent
from army.memory import MEMORY_RULES, Memory

META = {
    "category": "memory",
    "description": "A reflective journaling partner that remembers themes across entries and spots patterns over time.",
    "example": "Today was stressful: two deadlines moved up and I skipped the gym again.",
}
EVALS = [{"input": "I felt proud today: I finally shipped the side project.", "must_contain": ["?"], "max_seconds": 120}]


def build(llm=None, namespace: str = "journal"):
    mem = Memory(namespace)
    return Agent(
        name="journal-coach",
        instructions=f"""You are a warm, perceptive journaling coach.

{MEMORY_RULES}
Also remember a one-line summary of each entry with its date and the main theme.

Reply with: a short reflection on what you heard, any pattern you notice from recalled entries (be specific),
one open question, and one small, optional next step. Never diagnose. If the user mentions self-harm or a crisis,
encourage them warmly to contact a trusted person or a local professional or helpline.""",
        tools=mem.tools(),
        llm=llm,
    )
