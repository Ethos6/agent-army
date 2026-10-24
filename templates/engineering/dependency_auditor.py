"""Dependency Auditor

Checks a Python requirements file against live PyPI data: outdated pins, yanked releases,
backport packages that are obsolete on modern Python, standard-library modules listed as
dependencies, unpinned entries and conflicting duplicate constraints. Every finding comes with
the fix.
"""
from army import Agent
from army.tools import read_file
from army.web import pypi_package

META = {
    "category": "engineering",
    "description": "Audits requirements.txt against live PyPI: outdated, yanked, obsolete backports, duplicates, unpinned.",
    "example": "Audit examples/data/requirements-sample.txt for Python 3.12",
}
EVALS = [{"input": "Audit examples/data/requirements-sample.txt for Python 3.12", "must_contain": ["dataclasses", "flask"], "max_seconds": 240}]


def build(llm=None):
    return Agent(
        name="dependency-auditor",
        instructions="""You are a Python supply-chain reviewer. `read_file` the manifest, then call `pypi_package` for every
third-party package.

Check: standard-library modules listed as deps (e.g. typing), backports obsolete on the target Python (e.g. dataclasses),
outdated pins (how many major/minor versions behind), yanked versions, unpinned or loosely pinned entries, and duplicate or
conflicting constraints.

Output: | Package | Line | Issue | Severity | Fix |, then ## Suggested requirements file (complete, corrected).""",
        tools=[read_file, pypi_package],
        llm=llm,
        max_steps=16,
    )
