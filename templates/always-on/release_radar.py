"""Release Radar

Watches the GitHub releases of the projects you depend on and briefs you only on what matters:
breaking changes, deprecations, security fixes and major versions, with the action you need to take.
It remembers which releases it already reported. Schedule it weekly.
"""
from army import Agent
from army.memory import Memory
from army.web import github_releases

META = {
    "category": "always-on",
    "description": "Watches your dependencies' GitHub releases and flags breaking, security and deprecation changes.",
    "example": "Watch psf/requests, pallets/flask and pydantic/pydantic",
}
EVALS = [{"input": "Watch psf/requests", "must_contain": ["requests"], "max_seconds": 240}]


def build(llm=None, namespace: str = "release-radar"):
    mem = Memory(namespace)
    remember, recall, _ = mem.tools()
    return Agent(
        name="release-radar",
        instructions="""You run on a schedule. The request lists GitHub repos (owner/name).
For each repo: `recall` "reported <repo>", call `github_releases`, and consider only releases not yet reported.
Classify each change: BREAKING / SECURITY / DEPRECATION / MAJOR / minor. `remember` "reported <repo> <tag>" afterwards.
Output a table | Repo | Release | Type | What changed | Action needed |, then minor releases as one line each.
If nothing new, say so.""",
        tools=[remember, recall, github_releases],
        llm=llm,
        max_steps=20,
    )
