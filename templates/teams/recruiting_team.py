"""Recruiting Team

Screens a folder of resumes against a job description. A screener scores each candidate requirement
by requirement with quoted evidence, a hiring manager ranks the shortlist and checks for bias in the
reasoning, and a coordinator writes tailored interview plans and candidate emails.
"""
from army import Agent, Pipeline
from army.tools import list_files, read_file

META = {
    "category": "teams",
    "description": "Screener, hiring manager and coordinator rank resumes with evidence and plan the interviews.",
    "example": "Screen the resumes in examples/resumes against examples/resumes/job_description.md",
}
EVALS = [{"input": "Screen the resumes in examples/resumes against examples/resumes/job_description.md", "must_contain": ["Candidate A", "Interview plan"], "max_seconds": 300}]


def build(llm=None):
    screener = Agent("screener", """`list_files` the resume folder and `read_file` the job description and every resume.
For each candidate: | Requirement | Evidence (quote) | Score 0-2 |, a total, and location/timezone fit.
Judge only job-relevant evidence. Ignore names, age, gender, nationality and schools' prestige.""",
                     tools=[list_files, read_file], llm=llm, max_steps=12)
    manager = Agent("hiring-manager", """Rank the candidates from the screening. For each: advance / hold / reject with one-line reason.
Then do a bias check: does any reason rely on something not job-related? Correct it if so.""", llm=llm)
    coordinator = Agent("coordinator", """For advanced candidates write:
## Interview plan: <candidate>  (4 questions probing their specific gaps, plus what a strong answer shows)
## Emails  (invite for advanced candidates; kind, specific rejection for others)
Start with the final ranking table.""", llm=llm)
    return Pipeline(screener, manager, coordinator, name="recruiting-team")
