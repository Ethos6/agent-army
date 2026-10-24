"""Commit Explainer

Answers "why does this code exist?". Point it at a file or a line range and it walks the git history:
the commit that introduced the code, later changes, what changed alongside it, and the messages and
diffs that reveal intent. It separates what the history proves from what it only suggests.
"""
from army import Agent
from army.tools import git_blame, git_log, git_show, read_file

META = {
    "category": "engineering",
    "description": "Reconstructs why a file or code region exists from blame, introducing commits and later edits.",
    "example": "Why does army/agent.py parse JSON from code fences?",
}
EVALS = [{"input": "Explain the history of README.md", "must_contain": ["commit"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="commit-explainer",
        instructions="""You are a code archaeologist. Run inside a git repo.

1. `read_file` the target; `git_blame` the relevant lines to find the commits.
2. `git_show` the introducing commit and the most significant later ones; `git_log` the file for context.

Output:
## Short answer  (why it exists, 2-3 sentences)
## Timeline  (| Date | Commit | Author | What changed | Evidence |)
## Changed together  (other files touched in the same commits: what that suggests)
## Proven vs inferred  (separate what commit messages/diffs state from your interpretation)
## Safe to change?  (risks of modifying or deleting it)""",
        tools=[read_file, git_blame, git_log, git_show],
        llm=llm,
        max_steps=12,
    )
