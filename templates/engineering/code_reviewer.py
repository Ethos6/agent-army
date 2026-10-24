"""Code Reviewer

Run it inside any git repo. It reads the diff, opens surrounding files when it needs context, and
reports only the problems that matter, each with a severity, the exact input that triggers it and
the smallest fix. It ends with a machine-readable verdict you can gate CI on.
"""
from army import Agent
from army.tools import git_diff, list_files, read_file

META = {
    "category": "engineering",
    "description": "Reviews your git diff like a staff engineer: ranked bugs with a trigger scenario and a fix, no style nits.",
    "example": "Review my uncommitted changes",
}
EVALS = [{"input": "Review this pasted code:\ndef avg(xs):\n    return sum(xs) / len(xs)\n", "must_contain": ["empty", "Verdict"], "max_seconds": 120}]


def build(llm=None, ref: str = "HEAD"):
    return Agent(
        name="code-reviewer",
        instructions=f"""You are a staff engineer doing a pre-merge review.

1. Call `git_diff` with ref "{ref}" (or review the code the user pasted).
2. Open surrounding files with `read_file` when a change depends on code you can't see.
3. Report only real problems: bugs, security holes, data loss, races, broken error handling, missing tests for risky
   logic. Skip style nits a formatter would fix.

For each finding:
### [BLOCKER|MAJOR|MINOR] <file>:<line> - <title>
**Why it breaks:** a concrete input or sequence of events that triggers it.
**Fix:** the smallest change, as a code snippet.

End with `Verdict: APPROVE` or `Verdict: REQUEST CHANGES`. No findings means APPROVE.""",
        tools=[git_diff, read_file, list_files],
        llm=llm,
        max_steps=12,
    )
