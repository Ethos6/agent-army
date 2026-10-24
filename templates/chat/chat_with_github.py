"""Chat with a GitHub Repo

Ask anything about a public GitHub repository: what it does, how it's structured, where a feature
lives, how to run it, what changed recently. The agent reads the file tree and README, opens the
files it needs, and points you to exact paths. Set GITHUB_TOKEN for higher rate limits or private
repos.
"""
from army import Agent
from army.web import github_file, github_releases, github_repo

META = {
    "category": "chat",
    "description": "Ask about any GitHub repo: structure, where features live, how to run it, recent releases.",
    "example": "In python/cpython, where is the list sort algorithm implemented?",
}
EVALS = [{"input": "What does the repo psf/requests do and which file defines Session?", "must_contain": ["sessions.py"], "max_seconds": 180}]


def build(llm=None):
    return Agent(
        name="chat-with-github",
        instructions="""You are a senior engineer onboarding someone to a codebase. Start with `github_repo` (overview, tree, README).
Open specific files with `github_file` to confirm details; check `github_releases` for "what changed" questions.
Always cite exact paths (and quote short code when helpful). Never guess file contents you haven't opened.""",
        tools=[github_repo, github_file, github_releases],
        llm=llm,
        max_steps=10,
    )
