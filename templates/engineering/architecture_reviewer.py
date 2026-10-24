"""Architecture Reviewer

Reviews a codebase or a design document like a principal engineer. It maps the components and data
flow, then evaluates scalability, reliability, security, operability and cost, names the single
points of failure, and proposes a prioritized list of changes with effort estimates and a Mermaid
diagram of the current architecture.
"""
from army import Agent
from army.tools import list_files, read_file
from army.web import web_search

META = {
    "category": "engineering",
    "description": "Maps a codebase or design doc, finds failure points and risks, and proposes prioritized changes.",
    "example": "Review the architecture of this repository",
}
EVALS = [{"input": "Design: a single Postgres instance behind one API server handles 50k writes/sec for a chat app", "must_contain": ["single point of failure", "mermaid"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="architecture-reviewer",
        instructions="""You are a principal engineer. If reviewing a repo, `list_files` and `read_file` the entry points, configs
and core modules. Use `web_search` only to check limits of named technologies.

Output:
## Current architecture  (components, data flow, a ```mermaid flowchart)
## Assessment  (| Dimension | Rating | Evidence |) for scalability, reliability, security, operability, cost, simplicity
## Single points of failure
## Recommendations  (| Change | Why | Effort S/M/L | Priority |)
## What I'd leave alone""",
        tools=[list_files, read_file, web_search],
        llm=llm,
        max_steps=14,
    )
