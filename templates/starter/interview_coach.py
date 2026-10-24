"""Interview Coach

Prepares you for a specific interview. Give it the role and company (and optionally the job post
URL). It researches the company, predicts likely questions across behavioural, technical and
role-specific areas, and gives a model answer outline plus what a strong answer must include.
"""
from army import Agent
from army.tools import fetch_url
from army.web import web_search

META = {
    "category": "starter",
    "description": "Company research, the questions you'll likely get, and what a strong answer must include for each.",
    "example": "Product manager interview at a fintech startup, focus on payments",
}
EVALS = [{"input": "Junior data analyst interview at an e-commerce company", "must_contain": ["Question", "Strong answer"], "max_seconds": 180}]


def build(llm=None, questions: str = "10"):
    return Agent(
        name="interview-coach",
        instructions=f"""You are an interview coach who has sat on hundreds of hiring panels.

1. If a company is named, research it with `web_search` (product, recent news, values). Fetch a job post URL if given.
2. Write {questions} likely questions mixing behavioural, role-specific and company-specific ones.

For each:
### Question N: <question>
**Why they ask:** what it tests.
**Strong answer includes:** 3 bullets (structure such as STAR, specifics, a number).
**Red flags:** one line.

Finish with: 3 smart questions to ask the interviewer, and a 20-minute prep plan.""",
        tools=[web_search, fetch_url],
        llm=llm,
    )
