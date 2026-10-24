"""Scope Creep Checker

Compares a diff with its stated intent (the PR title or ticket). It groups every change into
"needed for the intent", "related but separable" and "unrelated", and recommends what to keep, split
into another PR, or justify, so reviews stay small and history stays readable.
"""
from army import Agent
from army.tools import git_diff, read_file

META = {
    "category": "engineering",
    "description": "Checks whether a diff grew beyond its stated intent; recommends what to keep, split or justify.",
    "example": "Intent: fix the login redirect bug. Check my uncommitted changes",
}
EVALS = [{"input": "Intent: fix a typo in README. Diff: README typo fix plus a new database migration and a dependency bump", "must_contain": ["Split", "Keep"], "max_seconds": 120}]


def build(llm=None, ref: str = "HEAD"):
    return Agent(
        name="scope-checker",
        instructions=f"""You are a reviewer who keeps pull requests focused. Get the diff with `git_diff` (ref "{ref}") unless it was
pasted. Take the stated intent from the request.

Classify every hunk or file:
| File / change | Category (Needed / Separable / Unrelated) | Reason |

Then: ## Keep  ## Split into separate PRs (suggested titles)  ## Justify in the description
## Verdict: FOCUSED or SCOPE CREEP (with the percentage of changed lines outside the intent).""",
        tools=[git_diff, read_file],
        llm=llm,
    )
