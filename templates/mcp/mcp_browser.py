"""Browser MCP Agent

Drives a real web browser through a browser-automation MCP server: navigate, read pages, click,
fill search boxes and extract results. It is useful for sites that need JavaScript. It never submits
payments, logs in or accepts terms on your behalf, and it describes every action it takes.
"""
from army import Agent
from army.mcp import MCPServer

META = {
    "category": "mcp",
    "description": "Drives a real browser over MCP for JavaScript-heavy sites; never logs in, pays or accepts terms.",
    "example": "Go to https://news.ycombinator.com and list the top 5 stories with their points",
    "needs": "Node.js (npx); the browser MCP server downloads a browser on first run.",
}
EVALS = [{"input": "Open https://example.org and tell me the page heading", "must_contain": ["Example Domain"], "max_seconds": 240}]


def build(llm=None, server: str = "npx -y @playwright/mcp@latest --headless"):
    browser = MCPServer(server, name="browser")
    return Agent(
        name="mcp-browser",
        instructions="""You operate a web browser via MCP. Call `browser_list_tools` first. Navigate, then read the page snapshot
before clicking. Narrate each action briefly. Never enter passwords or payment details, never log in, never accept
cookie banners beyond the minimum, and never submit forms that buy, post or delete anything.""",
        tools=browser.tools(),
        llm=llm,
        max_steps=20,
    )
