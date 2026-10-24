"""Incident Postmortem Writer

Turns raw incident notes, chat logs and timelines into a blameless postmortem: impact with numbers,
a clean timeline, root cause using the five whys, what went well, where we got lucky, and action
items that each have an owner placeholder, a due date and a type (prevent, detect, mitigate).
"""
from army import Agent
from army.tools import calculate, read_file

META = {
    "category": "engineering",
    "description": "Raw incident notes in, a blameless postmortem out: impact, timeline, five whys and owned actions.",
    "example": "14:02 deploy v2.3; 14:05 error rate 30%; 14:20 paged; 14:41 rollback; 14:45 recovered. Cause: missing DB index",
}
EVALS = [{"input": "09:00 cert expired on api; 09:00-09:52 all mobile logins failed; 09:52 renewed manually", "must_contain": ["Root cause", "Action items", "Impact"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="postmortem-writer",
        instructions="""You are an SRE lead writing a blameless postmortem. Read files with `read_file` if paths are given.
Compute durations with `calculate`.

# Postmortem: <title>
## Summary  ## Impact (duration, users/requests affected, revenue if known)
## Timeline (UTC table)  ## Root cause (five whys)  ## Contributing factors
## What went well  ## Where we got lucky
## Action items (| Action | Type: prevent/detect/mitigate | Owner [TBD] | Due |)
Use neutral language about people; focus on systems.""",
        tools=[read_file, calculate],
        llm=llm,
    )
