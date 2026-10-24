"""Game Design Team

A studio in a pipeline: a creative director sets the vision and pillars, a systems designer builds
the core loop and mechanics with numbers, a narrative designer writes the world and characters, and
a producer turns it into a scoped game design document with an MVP and milestones.
"""
from army import Agent, Pipeline
from army.tools import calculate

META = {
    "category": "teams",
    "description": "Creative director, systems designer, narrative designer and producer produce a scoped design doc.",
    "example": "A cozy co-op game about running a lighthouse on a stormy island, for Switch and PC",
}
EVALS = [{"input": "A roguelike deckbuilder about a cat burglar", "must_contain": ["Core loop", "MVP"], "max_seconds": 300}]


def build(llm=None):
    director = Agent("creative-director", """Define the vision: one-line pitch, target player, 3 design pillars, reference
games and what we do differently, and the feeling the player should have.""", llm=llm)
    systems = Agent("systems-designer", """Design the core loop (30-second, 5-minute, session), mechanics, progression and economy.
Give concrete numbers (costs, rates, timers) and check balance math with `calculate`.""", tools=[calculate], llm=llm)
    narrative = Agent("narrative-designer", """Write the world, tone, 3-5 characters with motivations, and how story is delivered
through play (not cutscenes only). Respect the pillars.""", llm=llm)
    producer = Agent("producer", """Assemble the game design document:
# <Title> - Game Design Document
## Vision  ## Core loop  ## Mechanics & economy  ## World & characters
## MVP scope (what's in / out)  ## Milestones (vertical slice, alpha, beta)  ## Biggest risks""", llm=llm)
    return Pipeline(director, systems, narrative, producer, name="game-design-team")
