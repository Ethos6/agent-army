"""Universal MCP Agent

Connect any Model Context Protocol server over stdio and use its tools from any model. Pass the
server command with --opt server="npx -y <package> <args>". The agent discovers the server's tools at
runtime and calls them; the server is only started when the agent first needs it.
"""
from army import Agent
from army.mcp import MCPServer

META = {
    "category": "mcp",
    "description": "Plug in any MCP server by command; the agent discovers and uses its tools on any model.",
    "example": "List the tools you have and show me what's in the current folder",
    "needs": "Node.js (npx) or the MCP server's own runtime.",
}
EVALS = [{"input": "List the tools you have", "must_contain": ["read"], "max_seconds": 180}]


def build(llm=None, server: str = "npx -y @modelcontextprotocol/server-filesystem ."):
    mcp = MCPServer(server, name="mcp")
    return Agent(
        name="mcp-agent",
        instructions=f"""You can use an MCP server ({server}). Always call `mcp_list_tools` first to learn its tools and
argument schemas, then use `mcp_call` with tool_name and an arguments object. Report what you did and the results.""",
        tools=mcp.tools(),
        llm=llm,
        max_steps=12,
    )
