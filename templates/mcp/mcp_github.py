"""GitHub MCP Agent

Explore and analyse GitHub in plain English through the GitHub MCP server: "what are the open bugs
labelled P1 in my repo?", "summarize PRs merged this week", "who are the most active reviewers?".
Read-only by default: it describes any write action and only performs it when the request clearly
asks.
"""
from army import Agent
from army.mcp import MCPServer

META = {
    "category": "mcp",
    "description": "Ask about issues, PRs and repos in plain English through the GitHub MCP server.",
    "example": "Summarize the open issues in python/cpython labelled 'type-bug' from the last week",
    "needs": "Node.js (npx) and GITHUB_PERSONAL_ACCESS_TOKEN in the environment.",
}
EVALS = [{"input": "What are the 3 most recently updated open issues in psf/requests?", "must_contain": ["#"], "max_seconds": 240}]


def build(llm=None):
    gh = MCPServer(["npx", "-y", "@modelcontextprotocol/server-github"], name="github")
    return Agent(
        name="mcp-github",
        instructions="""You analyse GitHub via MCP. Call `github_list_tools` first. Use search/list/get tools; summarise with links
(#number and URL). Do not create, comment, merge or close anything unless the user's request explicitly asks for it.""",
        tools=gh.tools(),
        llm=llm,
        max_steps=15,
    )
