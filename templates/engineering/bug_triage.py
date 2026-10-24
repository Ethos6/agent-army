"""Bug Triage

Paste a bug report, stack trace or error log. The agent reproduces the reasoning a senior on-call
engineer would: it locates the relevant code, forms ranked hypotheses for the root cause, says how
to confirm each one, proposes a fix, and assigns severity and a regression test.
"""
from army import Agent
from army.tools import git_log, list_files, read_file
from army.web import web_search

META = {
    "category": "engineering",
    "description": "Turns a bug report or stack trace into ranked root-cause hypotheses, a fix and a regression test.",
    "example": "Traceback: ZeroDivisionError in avg() at stats.py line 12 when the report has no rows",
}
EVALS = [{"input": "Users report KeyError: 'email' in signup handler when signing up with Google", "must_contain": ["Hypotheses", "Severity"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="bug-triage",
        instructions="""You are the senior on-call engineer.

1. Parse the report: symptom, trigger, environment, frequency.
2. If running in a repo, find the code with `list_files` / `read_file`; check recent changes with `git_log`.
3. Search known issues for library errors with `web_search`.

Output:
## Summary  ## Severity (S1-S4 with reason)
## Hypotheses  (ranked: cause, evidence, how to confirm in under 15 minutes)
## Proposed fix  (code)
## Regression test  (code)
## Ask the reporter  (missing info, if any)""",
        tools=[read_file, list_files, git_log, web_search],
        llm=llm,
        max_steps=12,
    )
