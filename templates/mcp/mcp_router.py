"""Multi-MCP Router

One agent, several MCP servers. Give it a set of servers (name=command;name=command) and it decides
which server's tools each step needs, so it can, for example, read local files with one server and
look things up with another in the same task. Each server starts only when first used.
"""
from army import Agent
from army.mcp import MCPServer

META = {
    "category": "mcp",
    "description": "Routes each step to the right one of several MCP servers, which start only when needed.",
    "example": "Read examples/knowledge-base/pricing.md and tell me which plans exist",
    "needs": "Node.js (npx) for the default servers.",
}
EVALS = [{"input": "Which servers and tools do you have?", "must_contain": ["fs"], "max_seconds": 180}]


def build(llm=None, servers: str = "fs=npx -y @modelcontextprotocol/server-filesystem .;memory=npx -y @modelcontextprotocol/server-memory"):
    tools, names = [], []
    for entry in servers.split(";"):
        name, _, cmd = entry.partition("=")
        name = name.strip()
        tools += MCPServer(cmd.strip(), name=name).tools()
        names.append(name)
    return Agent(
        name="mcp-router",
        instructions=f"""You have these MCP servers: {', '.join(names)}. Each has <name>_list_tools and <name>_call.
List a server's tools before first use. Pick the right server per step and explain your routing briefly.""",
        tools=tools,
        llm=llm,
        max_steps=20,
    )
