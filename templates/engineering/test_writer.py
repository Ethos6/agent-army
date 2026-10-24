"""Test Writer

Reads a source file and writes a thorough test file for it: happy paths, edge cases, error handling
and regression cases derived from the code's actual branches. It explains which behaviours are
covered and what it deliberately skipped, and saves the test file to outputs/.
"""
from army import Agent
from army.tools import list_files, read_file, write_file

META = {
    "category": "engineering",
    "description": "Writes branch-driven unit tests for a source file and saves them, with a coverage map.",
    "example": "Write unittest tests for army/rag.py",
}
EVALS = [{"input": "Write unittest tests for army/tools.py calculate()", "must_contain": ["outputs/", "test_"], "max_seconds": 180}]


def build(llm=None, framework: str = "unittest"):
    return Agent(
        name="test-writer",
        instructions=f"""You are a senior engineer who writes tests that catch real bugs. Use {framework}.

1. `read_file` the target and any module it imports from the same project.
2. List every branch, boundary and error path. Write one focused test per behaviour with a descriptive name.
3. No network or real API calls: use fakes. Keep tests deterministic.
4. Save with `write_file` as test_<module>.py.

Final answer: the file path, a coverage map (| Behaviour | Test name |), and anything you chose not to test and why.""",
        tools=[read_file, list_files, write_file],
        llm=llm,
    )
