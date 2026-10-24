"""Resume Tailor

Matches your resume against a job description (file, URL or pasted text). It scores the fit
requirement by requirement, rewrites your bullets to surface relevant evidence you already have,
and lists real gaps honestly. It never invents experience.
"""
from army import Agent
from army.tools import fetch_url, read_file

META = {
    "category": "starter",
    "description": "Requirement-by-requirement fit score, rewritten bullets from your real experience, and honest gaps.",
    "example": "Tailor examples/resumes/candidate_a.md to examples/resumes/job_description.md",
}
EVALS = [{"input": "Tailor examples/resumes/candidate_b.md to examples/resumes/job_description.md", "must_contain": ["Fit", "Gaps"], "max_seconds": 120}]


def build(llm=None):
    return Agent(
        name="resume-tailor",
        instructions="""You are a recruiter-turned-career-coach. Read the resume and the job description (`read_file` for paths,
`fetch_url` for links).

Output:
## Fit: N/10
| Requirement | Evidence in resume | Match (strong/partial/none) |
## Rewritten bullets
5-8 bullets using strong verbs and numbers ALREADY in the resume. Never add skills, employers or metrics that are not there.
## Gaps
Honest gaps and how to address each (project, course, or how to frame it in the interview).
## Keywords to include
Terms from the job description that an applicant-tracking system will look for.""",
        tools=[read_file, fetch_url],
        llm=llm,
    )
